# Phân tích candidate pool

| Variant | Topology hợp lệ | ΔE tốt nhất (%) | CI95 topology | Pool đủ | Feasible/attempt | Runtime thuật toán (s) |
|---|---:|---:|---|---:|---:|---:|
| B0 | 16 | 0.000 | — | 48/54 | 0.898 | 0.3206 |
| D0 | 16 | 0.090 | — | 48/54 | 0.925 | 0.5391 |
| D40total | 0 | — | — | 48/54 | 0.929 | 0.2727 |
| R0 | 16 | 0.333 | — | 48/54 | 0.900 | 0.1399 |
| V1-.25 | 16 | -0.080 | — | 48/54 | 0.900 | 0.3141 |
| V1-.5 | 16 | -0.652 | — | 48/54 | 0.899 | 0.3145 |
| V1-0 | 16 | -0.596 | — | 48/54 | 0.900 | 0.3293 |
| V2 | 16 | 3.491 | — | 54/54 | 0.967 | 0.8704 |
| V2+V5 | 16 | 7.946 | — | 54/54 | 0.987 | 0.8718 |
| V2+V6 | 16 | 7.735 | — | 54/54 | 0.994 | 0.8645 |
| V3 | 16 | -0.582 | — | 48/54 | 0.900 | 0.3437 |
| V4 | 16 | -1.126 | — | 48/54 | 0.899 | 0.3629 |
| V5 | 16 | -0.996 | — | 48/54 | 0.899 | 0.3691 |
| V6 | 16 | -0.636 | — | 48/54 | 0.898 | 0.3773 |
| V7 | 16 | -1.057 | — | 48/54 | 0.900 | 0.3518 |

Dấu dương = giảm năng lượng. CI dùng mean seed trong mỗi topology; chỉ bật khi scenario seeds độc lập. Không xem candidate/round là replicate. D40total cố ý pool20 nên không có pair pool40.

{"rows": 810, "topologies": 18, "invalid_probabilities": 0, "invalid_trees": 0, "incomplete_pools": 72, "full_evaluations": 33484, "interpretation": "D40total has 20 search+20 calibration and is intentionally excluded from 40-feasible paired energy table"}