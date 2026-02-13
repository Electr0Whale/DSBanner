# DSBanner

A collection of Python tools to extract and batch-edit banners (icons & titles) in Nintendo DS ROMs (.nds).
一套用于提取和批量编辑任天堂 DS (NDS) ROM 横幅（图标与标题）信息的 Python 工具集。

---

## 🛠 Features | 功能特性

### 1. extract_banner.py
**English:** Recursively scans a folder for `.nds` files and extracts all available language titles (Japanese, English, Chinese, etc.) from the ROM banner. The results are exported into a structured `banners.xml` file, preserving line breaks.

**中文：** 递归扫描文件夹中的 `.nds` 文件，提取 ROM 横幅中所有可用的语言标题（日语、英语、中文等）。结果将导出为结构化的 `banners.xml` 文件，并精准保留原始换行符。

### 2. nds_banner_editor.py
**English:** Automatically modifies ROM banners based on the filename. It reformats the banner into two lines: **Game Name** and **Translation Group**.
- **Auto-CRC16 Correction:** Automatically recalculates and fixes the Banner CRC16 to ensure the ROM remains bootable.
- **Batch Processing:** Handles hundreds of ROMs in seconds.
- **Error Logging:** Generates `modification_errors.xml` if the text exceeds the 256-byte limit or filename format is invalid.

**中文：** 根据文件名自动修改 ROM 横幅。它会将横幅重新排版为两行：**游戏名** 和 **汉化组**。
- **自动 CRC16 修复：** 自动重新计算并修复 Banner 校验码，确保修改后的 ROM 在实机或模拟器上正常运行。
- **批量处理：** 几秒钟内即可处理数百个 ROM。
- **错误日志：** 如果文本超过 256 字节限制或文件名格式不符，将生成 `modification_errors.xml` 详细记录原因。

---

## 📂 Filename Format Requirement | 文件名格式要求

For `nds_banner_editor.py`, your files should follow this pattern:
为了使编辑脚本正常工作，文件名应遵循以下格式：

`GameName(Region)(Translator)(Size).nds`  
*Example: `Mario Party(JP)(ACG-Hans)(512Mb).nds`*

---

## 🚀 Usage | 如何使用

1. **Clone the repo | 克隆仓库:**
   ```bash
   git clone [https://github.com/YourUsername/NDS-Banner-Lab.git](https://github.com/YourUsername/NDS-Banner-Lab.git)
   cd NDS-Banner-Lab

```

2. **Run the scripts | 运行脚本:**
```bash
# To extract | 提取横幅
python extract_banner.py

# To batch edit | 批量编辑
python nds_banner_editor.py

```



---

## ⚠️ Disclaimer | 免责声明

This tool modifies the binary data of ROM files. While it includes CRC16 protection and length checks, please **always back up your files** before running the batch editor. The developers are not responsible for any data loss.

本工具会修改 ROM 文件的二进制数据。虽然脚本包含 CRC16 校验修复和长度检查，但在运行批量修改之前，请**务必备份您的文件**。开发者对任何数据损坏概不负责。

```
