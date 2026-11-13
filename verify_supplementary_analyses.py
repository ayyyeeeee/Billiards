"""Independent numerical and artifact audit for the supplementary batch outputs."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np
import pandas as pd
from PIL import Image


def main():
    root = Path(__file__).resolve().parent
    out = root/'supplementary_figures'
    paired = pd.read_csv(out/'participant_paired_metrics.csv', dtype={'participant':str})
    checks = 0
    for _, row in paired.iterrows():
        for stage, suffix in [('baseline','pre'), ('test','post')]:
            files = [p for p in (root/row.participant/'processed_csv').rglob('*.csv')
                     if re.search(r'(?:^|_)'+stage+'_'+row.task+r'_', p.stem, re.I)]
            assert len(files) == 1, files
            data = pd.read_csv(files[0])
            ch = row.channel
            v = pd.to_numeric(data[ch+'_value'], errors='coerce')
            mask = np.isfinite(v) & data[ch+'_status'].astype(str).str.strip().str.lower().eq('scored')
            if ch+'_outlier' in data:
                mask &= ~pd.to_numeric(data[ch+'_outlier'], errors='coerce').eq(1)
            a = v[mask].to_numpy()
            assert len(a) == row['n_'+suffix]
            np.testing.assert_allclose(row['mae_'+suffix], np.abs(a).mean(), atol=1e-12)
            np.testing.assert_allclose(row['mse_'+suffix], np.mean(a*a), atol=1e-12)
            np.testing.assert_allclose(row['variance_'+suffix], np.var(a), atol=1e-12)
            np.testing.assert_allclose(row['bias_squared_'+suffix], np.mean(a)**2, atol=1e-12)
            checks += 1
    np.testing.assert_allclose(paired.delta_mse, paired.delta_bias_squared+paired.delta_variance, atol=1e-12)
    np.testing.assert_allclose(paired.delta_mse, paired.delta_corrected_bias_squared+paired.delta_sample_variance, atol=1e-12)
    artifacts = {}
    for png in sorted(out.glob('figure*.png')):
        with Image.open(png) as im:
            assert im.size == (3600,2400)
            assert abs(im.info['dpi'][0]-300)<.01
            artifacts[png.name] = dict(size=im.size, dpi=im.info['dpi'])
        pdf = png.with_suffix('.pdf').read_bytes()
        assert b'/FontFile2' in pdf
        assert b'/Subtype /Image' not in pdf
    assert len(artifacts) == 3
    hashes = json.loads((out/'source_hashes.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in hashes.items())
    for csv in out.glob('*.csv'):
        assert csv.read_bytes().startswith(b'\xef\xbb\xbf')
    result = dict(independent_raw_stage_checks=checks, participant_pair_checks=len(paired),
                  source_hashes_unchanged=len(hashes), artifacts=artifacts,
                  vector_pdf_checks='Embedded TrueType fonts; no raster image objects', csv_encoding='utf-8-sig')
    (out/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
