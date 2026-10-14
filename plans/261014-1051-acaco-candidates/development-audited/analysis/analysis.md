# Phân tích candidate pool

| Variant | Topology hợp lệ | ΔE tốt nhất (%) | CI95 topology | Pool đủ | Feasible/attempt | Runtime thuật toán (s) |
|---|---:|---:|---|---:|---:|---:|
| B0 | 1 | 0.000 | — | 10/10 | 1.000 | 0.1728 |
| D0 | 1 | 1.781 | — | 10/10 | 1.000 | 0.2996 |
| D40total | 0 | — | — | 10/10 | 1.000 | 0.1473 |
| R0 | 1 | 2.024 | — | 10/10 | 1.000 | 0.0752 |
| V1-.25 | 1 | 1.513 | — | 10/10 | 1.000 | 0.1665 |
| V1-.5 | 1 | 1.884 | — | 10/10 | 1.000 | 0.1848 |
| V1-0 | 1 | 2.212 | — | 10/10 | 1.000 | 0.1767 |
| V1-1 | 1 | 0.000 | — | 10/10 | 1.000 | 0.1898 |
| V2 | 1 | 4.927 | — | 10/10 | 1.000 | 0.4885 |
| V3 | 1 | -0.782 | — | 10/10 | 1.000 | 0.2088 |
| V4 | 1 | -0.898 | — | 10/10 | 1.000 | 0.2253 |
| V5 | 1 | -1.059 | — | 10/10 | 1.000 | 0.2215 |
| V6 | 1 | -1.682 | — | 10/10 | 1.000 | 0.2149 |
| V7 | 1 | 0.911 | — | 10/10 | 1.000 | 0.1989 |

Dấu dương = giảm năng lượng. CI dùng mean seed trong mỗi topology; chỉ bật khi scenario seeds độc lập. Không xem candidate/round là replicate. D40total cố ý pool20 nên không có pair pool40.

{"rows": 140, "topologies": 1, "invalid_probabilities": 0, "invalid_trees": 0, "incomplete_pools": 0, "full_evaluations": 6000, "interpretation": "D40total has 20 search+20 calibration and is intentionally excluded from 40-feasible paired energy table"}