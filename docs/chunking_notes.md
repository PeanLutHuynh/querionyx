# Chunking Benchmark Notes

## Benchmark Setup

- Sample files:
  - fpt_2023.pdf
  - fpt_2024.pdf

## Comparison Table

| Strategy | Total Chunks | Avg Tokens/Chunk | Min Tokens | Max Tokens |
| --- | ---: | ---: | ---: | ---: |
| Fixed-size | 2399 | 93.16 | 3 | 124 |
| Recursive Splitting | 2446 | 91.27 | 4 | 121 |
| Semantic Chunking | 1008 | 215.35 | 2 | 763 |

## Sample Chunks

### Fixed-size

#### Chunk 1

```
ĐỈNH CAO MỚI 
VƯƠN TẦM 
DẪN LỐI
BÁO CÁO THƯỜNG NIÊN FPT 2023
```

#### Chunk 2

```
ĐỈNH CAO MỚI
VƯƠN TẦM DẪN LỐI
Ngay từ khi thành lập, các nhà sáng lập FPT đã hướng đến “xây dựng một tổ chức kiểu mới, hùng mạnh bằng nỗ lực lao động 
sáng tạo trong khoa học kỹ thuật và công nghệ, làm khách hàng hài lòng, góp phần hưng thịnh quốc gia”.
FPT đã không ngừng dấn thân, đón đầu xu thế, vượt qua các giới hạn, biến cơ hội thành kết quả. 2023, ở cột mốc 35 năm, 
FPT đã khẳng định đẳng cấp mới trên toàn cầu: gia nhập nhóm doanh nghiệp dịch vụ CNTT tỷ USD. Năng lực
```

#### Chunk 3

```
công nghệ, đặc biệt trong những lĩnh vực công nghệ mới, không ngừng được khách hàng, đối tác, các tổ chức uy tín trên 
thế giới ghi nhận. Trong nước, FPT tiếp tục khẳng định vai trò đối tác chuyển đổi số, chuyển đổi xanh hàng đầu của các 
doanh nghiệp TOP VNR500 và các tổ chức, địa phương trên toàn quốc. Bước sang năm 2024, FPT tiếp tục đổi mới, sáng tạo, 
dẫn đầu xu thế để bứt phá mạnh mẽ trên hành trình chinh phục những đỉnh cao mới.
```

### Recursive Splitting

#### Chunk 1

```
ĐỈNH CAO MỚI 
VƯƠN TẦM 
DẪN LỐI
BÁO CÁO THƯỜNG NIÊN FPT 2023
```

#### Chunk 2

```
ĐỈNH CAO MỚI
VƯƠN TẦM DẪN LỐI
Ngay từ khi thành lập, các nhà sáng lập FPT đã hướng đến “xây dựng một tổ chức kiểu mới, hùng mạnh bằng nỗ lực lao động 
sáng tạo trong khoa học kỹ thuật và công nghệ, làm khách hàng hài lòng, góp phần hưng thịnh quốc gia”.
FPT đã không ngừng dấn thân, đón đầu xu thế, vượt qua các giới hạn, biến cơ hội thành kết quả. 2023, ở cột mốc 35 năm, 
FPT đã khẳng định đẳng cấp mới trên toàn cầu: gia nhập nhóm doanh nghiệp dịch vụ CNTT tỷ USD. Năng lực
```

#### Chunk 3

```
công nghệ, đặc biệt trong những lĩnh vực công nghệ mới, không ngừng được khách hàng, đối tác, các tổ chức uy tín trên 
thế giới ghi nhận. Trong nước, FPT tiếp tục khẳng định vai trò đối tác chuyển đổi số, chuyển đổi xanh hàng đầu của các 
doanh nghiệp TOP VNR500 và các tổ chức, địa phương trên toàn quốc. Bước sang năm 2024, FPT tiếp tục đổi mới, sáng tạo, 
dẫn đầu xu thế để bứt phá mạnh mẽ trên hành trình chinh phục những đỉnh cao mới.
```

### Semantic Chunking

#### Chunk 1

```
ĐỈNH CAO MỚI 
VƯƠN TẦM 
DẪN LỐI
BÁO CÁO THƯỜNG NIÊN FPT 2023
```

#### Chunk 2

```
ĐỈNH CAO MỚI
VƯƠN TẦM DẪN LỐI
Ngay từ khi thành lập, các nhà sáng lập FPT đã hướng đến “xây dựng một tổ chức kiểu mới, hùng mạnh bằng nỗ lực lao động 
sáng tạo trong khoa học kỹ thuật và công nghệ, làm khách hàng hài lòng, góp phần hưng thịnh quốc gia”. FPT đã không ngừng dấn thân, đón đầu xu thế, vượt qua các giới hạn, biến cơ hội thành kết quả. 2023, ở cột mốc 35 năm, 
FPT đã khẳng định đẳng cấp mới trên toàn cầu: gia nhập nhóm doanh nghiệp dịch vụ CNTT tỷ USD. Năng lực 
công nghệ, đặc biệt trong những lĩnh vực công nghệ mới, không ngừng được khách hàng, đối tác, các tổ chức uy tín trên 
thế giới ghi nhận.
```

#### Chunk 3

```
Trong nước, FPT tiếp tục khẳng định vai trò đối tác chuyển đổi số, chuyển đổi xanh hàng đầu của các 
doanh nghiệp TOP VNR500 và các tổ chức, địa phương trên toàn quốc. Bước sang năm 2024, FPT tiếp tục đổi mới, sáng tạo, 
dẫn đầu xu thế để bứt phá mạnh mẽ trên hành trình chinh phục những đỉnh cao mới.
```
