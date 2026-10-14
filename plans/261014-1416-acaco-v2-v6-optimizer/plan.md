# Kiểm tra parameter optimizer cho AC-ACO-V2-V6

- [x] Đọc actual optimizer/adapters/search-space, xác nhận current controller chỉ tuning D-ACO.
- [x] Tách lệnh smoke riêng: baseline + hai sampler proposals, tối đa3 trials/10 physical rounds/3 seeds/N200.
- [x] Cài dependencies thiếu, kiểm tra adapter đúng V2+V6 preset và fixed operator/ant/bounds/objective.
- [x] Unit tests parameter validation/equivalence/spawn/CLI và chạy actual smoke3trials×3rounds×2seeds.
- [x] Review độc lập, ghi kết quả/command/limitations tiếng Việt và source fingerprint.

Không đổi engine D-ACO hoặc production defaults. Meta-objective smoke là mean short physical energy, không phải service-lifetime+2% constraint của D campaign. Không chọn optimum/default/lifetime winner từ smoke. Campaign mới không cần legacy vì baseline là reported preset đang có.
