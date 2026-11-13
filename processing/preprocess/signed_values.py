# -*- coding: utf-8 -*-
"""
实验 CSV 数据批处理程序 (支持编号 01-30 自动批处理，严格按目标线/中心线判定正负)
功能说明：
1. 自动识别文件名中的模式 (both / strength / angle)：
   - strength 模式：修改 strength_value 的正负号（自动补全缺失杆），并计算力量的 mean 和 variance
   - angle 模式：修改 angle_value 的正负号（自动补全缺失杆），并计算角度的 mean 和 variance
   - both 模式：同时修改 strength_value 和 angle_value 的正负号，并计算两者的 mean 和 variance
2. 严格按目标线/中轴线分割的正负号规则（仅影响 strength_value 和 angle_value）：
   - 力量 (strength_value)：严格以目标线 (y_line(x)) 为分界：
     * 过线 (y > y_line，即 plane_signed > 0) -> 正数 (+abs)
     * 没过线 (y < y_line，即 plane_signed < 0) -> 负数 (-abs)
     * 在线上 (y == y_line，即 val == 0) -> 0
   - 角度 (angle_value)：严格以球台中轴线 (x_c) 为分界：
     * 击打左侧 (angle_end_plane_x < x_c) -> 负数 (-abs)
     * 击打右侧 (angle_end_plane_x > x_c) -> 正数 (+abs)
     * 在中轴线上 (angle_end_plane_x == x_c 或 val == 0) -> 0
3. 缺失值自动补全机制：
   - 当 strength_value 为空时，依次读取 strength_unconfirmed_estimate / strength_uncapped / uncapped_value，
     若仍为空（如 01_02 的第 8 杆），直接由终点坐标相对目标线的有向距离方程 (a*x + b*y + c) 精确算出带符号的力量值。
"""

import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# ======================== 配置区 ========================
# 实验根目录
from common.paths import PARTICIPANT_ROOT
BASE_DIR = PARTICIPANT_ROOT

# 源 CSV 相对于编号文件夹 (如 D:\experiment\01) 的子路径
SOURCE_REL_PATH = Path("MOLT4_results") / "csv"

# 处理后新文件备份相对于编号文件夹的子路径 (如 D:\experiment\01\processed_csv)
BACKUP_REL_PATH = Path("processed_csv")

# 方差自由度：1 表示样本方差 (Excel 的 VAR.S，科研统计默认)，0 表示总体方差 (Excel 的 VAR.P)
VARIANCE_DDOF = 1

# 统计量写入方式：
# "columns" -> 在表头新增 strength_mean, strength_variance, angle_mean, angle_variance 四列
# "rows"    -> 在表格底部追加 mean 和 variance 两行
# "both"    -> 同时新增统计列并在底部追加汇总行
SUMMARY_OUTPUT_MODE = "columns"

# 默认球台几何标定参数（程序会根据每个文件的数据自动微调校准）
DEFAULT_CENTER_X = 0.505414
DEFAULT_ORIGIN_X = 0.494839
DEFAULT_ORIGIN_Y = 1.497243
DEFAULT_THETA0_DEG = 0.408445

# 力量相对目标线的有向标定方程系数: signed_strength = STR_A * x + STR_B * y + STR_C
# 当球正好停在目标线上时 signed_strength = 0；过线 > 0；未过线 < 0
DEFAULT_STR_A = 0.009579041131223308
DEFAULT_STR_B = 0.6739826874887913
DEFAULT_STR_C = -1.0138556776522918
# ========================================================


def detect_file_mode(filepath: Path, df: pd.DataFrame) -> str:
    """根据文件名（优先）或表格 mode 列识别当前文件属于 both / strength / angle。"""
    name_lower = filepath.name.lower()
    if "both" in name_lower:
        return "both"
    if "strength" in name_lower:
        return "strength"
    if "angle" in name_lower:
        return "angle"

    if "mode" in df.columns:
        modes = df["mode"].dropna().astype(str).str.lower().unique()
        if len(modes) > 0:
            if "both" in modes:
                return "both"
            if "strength" in modes:
                return "strength"
            if "angle" in modes:
                return "angle"
    return "both"


def calibrate_strength_plane(df: pd.DataFrame) -> tuple[float, float, float]:
    """
    从当前文件已有的有效行和过线点 (strength_crossing_plane_x/y) 自动校准目标线方程：
    signed_strength = a * x + b * y + c（在目标线上恒为 0，过线 > 0，未过线 < 0）。
    """
    x_col = "strength_end_plane_x" if "strength_end_plane_x" in df.columns else (
        "end_plane_x" if "end_plane_x" in df.columns else None
    )
    y_col = "strength_end_plane_y" if "strength_end_plane_y" in df.columns else (
        "end_plane_y" if "end_plane_y" in df.columns else None
    )
    reason_col = "strength_stop_reason" if "strength_stop_reason" in df.columns else (
        "stop_reason" if "stop_reason" in df.columns else None
    )

    if x_col is None or y_col is None:
        return DEFAULT_STR_A, DEFAULT_STR_B, DEFAULT_STR_C

    pts_x, pts_y, pts_v = [], [], []

    # 1) 过线点本身严格位于目标线上，其有向力量值为 0
    if "strength_crossing_plane_x" in df.columns and "strength_crossing_plane_y" in df.columns:
        cx_s = pd.to_numeric(df["strength_crossing_plane_x"], errors="coerce")
        cy_s = pd.to_numeric(df["strength_crossing_plane_y"], errors="coerce")
        for idx in df.index:
            if pd.notna(cx_s.loc[idx]) and pd.notna(cy_s.loc[idx]):
                pts_x.append(float(cx_s.loc[idx]))
                pts_y.append(float(cy_s.loc[idx]))
                pts_v.append(0.0)

    # 2) 已明确计分的行
    for idx in df.index:
        xv = df.loc[idx, x_col]
        yv = df.loc[idx, y_col]
        if pd.isna(xv) or pd.isna(yv):
            continue
        raw_v = np.nan
        for c in ("uncapped_value", "strength_uncapped", "strength_value", "strength_unconfirmed_estimate"):
            if c in df.columns and pd.notna(df.loc[idx, c]):
                raw_v = float(df.loc[idx, c])
                break
        if np.isnan(raw_v):
            continue

        reason = ""
        if reason_col is not None and pd.notna(df.loc[idx, reason_col]):
            reason = str(df.loc[idx, reason_col]).strip().lower()

        if "crossing" in reason:
            signed_v = abs(raw_v)
        elif reason == "stationary":
            signed_v = -abs(raw_v)
        else:
            # 用默认目标线判断该校准点的正负
            default_signed = DEFAULT_STR_A * float(xv) + DEFAULT_STR_B * float(yv) + DEFAULT_STR_C
            signed_v = abs(raw_v) if default_signed >= 0 else -abs(raw_v)

        pts_x.append(float(xv))
        pts_y.append(float(yv))
        pts_v.append(signed_v)

    if len(pts_x) >= 4:
        A = np.column_stack([pts_x, pts_y, np.ones(len(pts_x))])
        coef, _, rank, _ = np.linalg.lstsq(A, pts_v, rcond=None)
        if rank == 3 and np.max(np.abs(A @ coef - pts_v)) < 1e-3:
            return float(coef[0]), float(coef[1]), float(coef[2])

    return DEFAULT_STR_A, DEFAULT_STR_B, DEFAULT_STR_C


def estimate_center_x(df: pd.DataFrame) -> float:
    """利用表格中的 angle_end_plane_x, angle_end_plane_y 和 angle_raw_degrees 自动校准球台中心线 x_c。"""
    x_col = "angle_end_plane_x" if "angle_end_plane_x" in df.columns else (
        "end_plane_x" if "end_plane_x" in df.columns else None
    )
    y_col = "angle_end_plane_y" if "angle_end_plane_y" in df.columns else (
        "end_plane_y" if "end_plane_y" in df.columns else None
    )

    if x_col is None:
        return DEFAULT_CENTER_X

    if y_col is not None and "angle_raw_degrees" in df.columns:
        valid = df[[x_col, y_col, "angle_raw_degrees"]].dropna()
        if not valid.empty:
            x = pd.to_numeric(valid[x_col], errors="coerce").values
            y = pd.to_numeric(valid[y_col], errors="coerce").values
            deg = pd.to_numeric(valid["angle_raw_degrees"], errors="coerce").values
            mask = ~(np.isnan(x) | np.isnan(y) | np.isnan(deg))
            if np.any(mask):
                x, y, deg = x[mask], y[mask], deg[mask]
                dx = (DEFAULT_ORIGIN_Y - y) * np.tan(np.radians(np.abs(deg)))
                cand_right = x - dx
                cand_left = x + dx
                best_cands = np.where(
                    np.abs(cand_right - DEFAULT_CENTER_X) <= np.abs(cand_left - DEFAULT_CENTER_X),
                    cand_right,
                    cand_left,
                )
                return float(np.median(best_cands))

    return DEFAULT_CENTER_X


def apply_strength_sign_and_fill(df: pd.DataFrame) -> pd.Series:
    """
    严格根据目标线分割确定 strength_value 的正负号，并自动补全缺失值：
    - 只要过线 (plane_signed > 0) -> 正数 (+abs)
    - 只要没过线 (plane_signed < 0) -> 负数 (-abs)
    - 如果在线上 (plane_signed == 0 或 val == 0) -> 0.0
    """
    if "strength_value" not in df.columns:
        return pd.Series(dtype=float)

    s_val = pd.to_numeric(df["strength_value"], errors="coerce")
    reason_col = "strength_stop_reason" if "strength_stop_reason" in df.columns else (
        "stop_reason" if "stop_reason" in df.columns else None
    )
    x_col = "strength_end_plane_x" if "strength_end_plane_x" in df.columns else (
        "end_plane_x" if "end_plane_x" in df.columns else None
    )
    y_col = "strength_end_plane_y" if "strength_end_plane_y" in df.columns else (
        "end_plane_y" if "end_plane_y" in df.columns else None
    )

    str_a, str_b, str_c = calibrate_strength_plane(df)
    signed_vals = s_val.copy()

    for idx in df.index:
        val = s_val.loc[idx]
        # 1) 若 strength_value 为空，优先从备用列提取数值
        if pd.isna(val):
            for fallback_col in ("strength_unconfirmed_estimate", "strength_uncapped", "uncapped_value"):
                if fallback_col in df.columns and pd.notna(df.loc[idx, fallback_col]):
                    val = float(df.loc[idx, fallback_col])
                    break

        # 2) 计算终点相对于目标线的有向值 plane_signed (过线 > 0，未过线 < 0，线上 == 0)
        plane_signed = np.nan
        if x_col is not None and y_col is not None:
            if pd.notna(df.loc[idx, x_col]) and pd.notna(df.loc[idx, y_col]):
                xv = float(df.loc[idx, x_col])
                yv = float(df.loc[idx, y_col])
                plane_signed = str_a * xv + str_b * yv + str_c

        # 若仍无数值，则直接采用目标线有向距离绝对值
        if pd.isna(val) and not np.isnan(plane_signed):
            val = round(abs(plane_signed), 6)

        if pd.isna(val):
            continue

        # 若数值为 0（刚好在线上），直接设为 0.0
        if abs(val) == 0.0 or (not np.isnan(plane_signed) and abs(plane_signed) < 1e-12):
            signed_vals.loc[idx] = 0.0
            continue

        # 3) 严格根据是否越过目标线确定正负号：
        # 优先使用精确坐标相对于目标线的位置 plane_signed 判定（过线为正，没过线为负）；
        # 若该行无坐标，则由 stop_reason 兜底判定。
        if not np.isnan(plane_signed):
            if plane_signed > 0:
                signed_vals.loc[idx] = abs(val)
            elif plane_signed < 0:
                signed_vals.loc[idx] = -abs(val)
            else:
                signed_vals.loc[idx] = 0.0
        else:
            reason = ""
            if reason_col is not None and pd.notna(df.loc[idx, reason_col]):
                reason = str(df.loc[idx, reason_col]).strip().lower()
            if "crossing" in reason:
                signed_vals.loc[idx] = abs(val)
            else:
                signed_vals.loc[idx] = -abs(val)

    return signed_vals


def apply_angle_sign_and_fill(df: pd.DataFrame) -> pd.Series:
    """
    严格根据球台中轴线判断角度是击打左侧还是右侧，并自动补全缺失值：
    - 左侧 (angle_end_plane_x < center_x) -> 负数 (-abs)
    - 右侧 (angle_end_plane_x > center_x) -> 正数 (+abs)
    - 在中轴线上 (angle_end_plane_x == center_x 或 val == 0) -> 0.0
    """
    if "angle_value" not in df.columns:
        return pd.Series(dtype=float)

    a_val = pd.to_numeric(df["angle_value"], errors="coerce")
    x_col = "angle_end_plane_x" if "angle_end_plane_x" in df.columns else (
        "end_plane_x" if "end_plane_x" in df.columns else None
    )
    y_col = "angle_end_plane_y" if "angle_end_plane_y" in df.columns else (
        "end_plane_y" if "end_plane_y" in df.columns else None
    )
    center_x = estimate_center_x(df)

    signed_vals = a_val.copy()
    for idx in df.index:
        val = a_val.loc[idx]
        if pd.isna(val):
            for fallback_col in ("angle_uncapped", "angle_raw_degrees", "uncapped_value"):
                if fallback_col in df.columns and pd.notna(df.loc[idx, fallback_col]):
                    val = round(float(df.loc[idx, fallback_col]), 2)
                    break
        if pd.isna(val) and x_col is not None and y_col is not None:
            if pd.notna(df.loc[idx, x_col]) and pd.notna(df.loc[idx, y_col]):
                xv = float(df.loc[idx, x_col])
                yv = float(df.loc[idx, y_col])
                ang = np.degrees(np.arctan2(xv - DEFAULT_ORIGIN_X, DEFAULT_ORIGIN_Y - yv)) - DEFAULT_THETA0_DEG
                val = round(abs(ang), 2)

        if pd.isna(val):
            continue

        if abs(val) == 0.0:
            signed_vals.loc[idx] = 0.0
            continue

        if x_col is not None and pd.notna(df.loc[idx, x_col]):
            x_end = float(df.loc[idx, x_col])
            if x_end < center_x:
                signed_vals.loc[idx] = -abs(val)
            elif x_end > center_x:
                signed_vals.loc[idx] = abs(val)
            else:
                signed_vals.loc[idx] = 0.0
        else:
            signed_vals.loc[idx] = val

    return signed_vals


def process_single_csv(src_file: Path, dst_file: Path) -> dict:
    """处理单个 CSV 文件并保存到备份路径。"""
    df = pd.read_csv(src_file)
    file_mode = detect_file_mode(src_file, df)

    s_mean, s_var = np.nan, np.nan
    a_mean, a_var = np.nan, np.nan

    # 1. 处理力量 (strength 或 both)
    if file_mode in ("strength", "both") and "strength_value" in df.columns:
        df["strength_value"] = apply_strength_sign_and_fill(df)
        valid_s = df["strength_value"].dropna()
        if len(valid_s) > 0:
            s_mean = float(valid_s.mean())
        if len(valid_s) > VARIANCE_DDOF:
            s_var = float(valid_s.var(ddof=VARIANCE_DDOF))

    # 2. 处理角度 (angle 或 both)
    if file_mode in ("angle", "both") and "angle_value" in df.columns:
        df["angle_value"] = apply_angle_sign_and_fill(df)
        valid_a = df["angle_value"].dropna()
        if len(valid_a) > 0:
            a_mean = float(valid_a.mean())
        if len(valid_a) > VARIANCE_DDOF:
            a_var = float(valid_a.var(ddof=VARIANCE_DDOF))

    # 3. 写入 mean 和 variance
    if SUMMARY_OUTPUT_MODE in ("columns", "both"):
        insert_pos = (
            df.columns.get_loc("angle_value") + 1
            if "angle_value" in df.columns
            else len(df.columns)
        )
        stat_cols = [
            ("strength_mean", round(s_mean, 6) if pd.notna(s_mean) else np.nan),
            ("strength_variance", round(s_var, 6) if pd.notna(s_var) else np.nan),
            ("angle_mean", round(a_mean, 6) if pd.notna(a_mean) else np.nan),
            ("angle_variance", round(a_var, 6) if pd.notna(a_var) else np.nan),
        ]
        for offset, (col_name, stat_val) in enumerate(stat_cols):
            col_series = pd.Series([np.nan] * len(df), index=df.index, dtype=float)
            if len(df) > 0:
                col_series.iloc[0] = stat_val
            if col_name in df.columns:
                df[col_name] = col_series
            else:
                df.insert(insert_pos + offset, col_name, col_series)

    if SUMMARY_OUTPUT_MODE in ("rows", "both"):
        mean_row = {col: np.nan for col in df.columns}
        var_row = {col: np.nan for col in df.columns}
        mean_row["shot"] = "mean"
        var_row["shot"] = "variance"
        mean_row["mode"] = file_mode
        var_row["mode"] = file_mode
        if "strength_value" in df.columns and pd.notna(s_mean):
            mean_row["strength_value"] = round(s_mean, 6)
            var_row["strength_value"] = round(s_var, 6) if pd.notna(s_var) else np.nan
        if "angle_value" in df.columns and pd.notna(a_mean):
            mean_row["angle_value"] = round(a_mean, 6)
            var_row["angle_value"] = round(a_var, 6) if pd.notna(a_var) else np.nan
        df = pd.concat([df, pd.DataFrame([mean_row, var_row])], ignore_index=True)

    dst_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dst_file, index=False, encoding="utf-8-sig")

    return {
        "file": src_file.name,
        "mode": file_mode,
        "strength_mean": s_mean,
        "strength_variance": s_var,
        "angle_mean": a_mean,
        "angle_variance": a_var,
        "dst": str(dst_file),
    }


def parse_folder_selection(user_input: str) -> list[str]:
    """解析用户输入的文件夹编号（支持 01、01-30、1 3 5 或回车全部处理）。"""
    text = user_input.strip().lower()
    if not text or text == "all":
        return [f"{i:02d}" for i in range(1, 31)]

    folders = []
    tokens = re.split(r"[,;\s]+", text)
    for tok in tokens:
        if not tok:
            continue
        if "-" in tok or "~" in tok:
            parts = re.split(r"[-~]", tok)
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start, end = int(parts[0]), int(parts[1])
                for i in range(min(start, end), max(start, end) + 1):
                    folders.append(f"{i:02d}")
        elif tok.isdigit():
            folders.append(f"{int(tok):02d}")
        else:
            folders.append(tok)
    return list(dict.fromkeys(folders))


def process_experiment_folders(folder_ids: list[str], base_dir: Path = BASE_DIR) -> None:
    """批量处理指定编号的实验文件夹。"""
    total_files = 0
    for fid in folder_ids:
        src_dir = base_dir / fid / SOURCE_REL_PATH
        dst_dir = base_dir / fid / BACKUP_REL_PATH

        if not src_dir.exists():
            print(f"[跳过] 编号 {fid}: 未找到源文件夹 {src_dir}")
            continue

        csv_files = sorted(src_dir.glob("*.csv"))
        if not csv_files:
            print(f"[跳过] 编号 {fid}: {src_dir} 中没有 CSV 文件")
            continue

        print(f"\n========== 正在处理编号 [{fid}] (共 {len(csv_files)} 个文件) ==========")
        for csv_path in csv_files:
            dst_path = dst_dir / csv_path.name
            try:
                info = process_single_csv(csv_path, dst_path)
                total_files += 1
                s_str = (
                    f"力量 Mean={info['strength_mean']:.4f}, Var={info['strength_variance']:.4f}"
                    if pd.notna(info["strength_mean"])
                    else "力量: 无"
                )
                a_str = (
                    f"角度 Mean={info['angle_mean']:.4f}, Var={info['angle_variance']:.4f}"
                    if pd.notna(info["angle_mean"])
                    else "角度: 无"
                )
                print(f"  [成功] {info['file']} ({info['mode']}) -> {s_str} | {a_str}")
            except Exception as exc:
                print(f"  [错误] 处理 {csv_path.name} 失败: {exc}")

        print(f"  -> 已备份至: {dst_dir}")

    print(f"\n批处理完成！共成功处理 {total_files} 个 CSV 文件。")


if __name__ == "__main__":
    print("=" * 65)
    print("  实验 CSV 自动批处理程序 (支持 strength / angle / both 自动识别)")
    print(f"  默认实验根目录: {BASE_DIR}")
    print("=" * 65)

    if len(sys.argv) > 1:
        raw_arg = " ".join(sys.argv[1:])
    else:
        raw_arg = input(
            "请输入要处理的文件夹编号 (如 01、01-30、1 3 5，直接回车默认处理 01-30 全部): "
        )

    selected_folders = parse_folder_selection(raw_arg)
    process_experiment_folders(selected_folders)

    if len(sys.argv) <= 1:
        input("\n按回车键退出...")