# Phân tích candidate pool

| Variant | Topology hợp lệ | ΔE tốt nhất (%) | CI95 topology | Pool đủ | Feasible/attempt | Runtime thuật toán (s) |
|---|---:|---:|---|---:|---:|---:|
| B0 | 17 | 0.000 | [0.000; 0.000] | 33/36 | 0.923 | 0.2839 |
| D0 | 16 | 0.412 | [-1.247; 2.072] | 32/36 | 0.940 | 0.4851 |
| D40total | 0 | — | — | 36/36 | 0.961 | 0.2697 |
| R0 | 17 | -1.059 | [-2.519; 0.400] | 34/36 | 0.921 | 0.1218 |
| V2 | 17 | 2.474 | [0.401; 4.546] | 34/36 | 0.939 | 0.8805 |
| V2+V5 | 17 | 6.730 | [5.881; 7.578] | 34/36 | 0.943 | 0.7268 |
| V2+V6 | 17 | 7.094 | [6.040; 8.148] | 34/36 | 0.946 | 0.7529 |
| V5 | 17 | -1.445 | [-2.944; 0.054] | 34/36 | 0.923 | 0.2853 |
| V6 | 17 | -1.872 | [-3.261; -0.483] | 34/36 | 0.922 | 0.2714 |

Dấu dương = giảm năng lượng. CI dùng mean seed trong mỗi topology; chỉ bật khi scenario seeds độc lập. Không xem candidate/round là replicate. D40total cố ý pool20 nên không có pair pool40.

{"rows": 324, "topologies": 18, "invalid_probabilities": 0, "invalid_trees": 0, "incomplete_pools": 19, "full_evaluations": 14260, "interpretation": "D40total has 20 search+20 calibration and is intentionally excluded from 40-feasible paired energy table"}