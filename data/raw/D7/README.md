# D7 — ขอบเขตการปกครอง (OCHA/HDX COD-AB)

ไฟล์ `tha_admin_boundaries.xlsx` (ตาราง lookup รหัสจังหวัดและอำเภอ) อยู่ใน repo แล้ว

ส่วน shapefile ไม่ได้อยู่ใน repo เพราะ `tha_admin2.shp` มีขนาด 103 MB เกินขีดจำกัด 100 MB ต่อไฟล์ของ GitHub ต้องดาวน์โหลดเอง

1. ดาวน์โหลด shapefile จาก [OCHA/HDX — Thailand Subnational Administrative Boundaries](https://data.humdata.org/m/dataset/cod-ab-tha) (ใช้ชุดขอบเขตปี 2565)
2. แตกไฟล์ไว้ในโฟลเดอร์ `data/raw/D7/shp/` ให้มีไฟล์อย่างน้อยดังนี้

```
data/raw/D7/shp/
├── tha_admin1.shp  .shx  .dbf  .prj  .cpg   ← จังหวัด
└── tha_admin2.shp  .shx  .dbf  .prj  .cpg   ← อำเภอ
```

ต้องใช้ shapefile เฉพาะตอนรันขั้นที่ 4–5 (Q2 และข้อมูล dashboard) ถ้าแค่อยากดูผล ไฟล์ใน `outputs/` และ `processed/geo/` มีครบแล้ว
