import os
import struct
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- CRC16 算法 ---
def calc_crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def save_xml(root, filename):
    xml_str = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent="  ")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(xml_str)

# --- 核心修改逻辑 ---
def apply_banner_update(file_path, filename, new_banner_text, error_root):
    try:
        with open(file_path, "r+b") as f:
            f.seek(0x68)
            banner_offset = struct.unpack("<I", f.read(4))[0]
            if banner_offset == 0: return False, "无Banner偏移量"

            f.seek(banner_offset)
            version = struct.unpack("<H", f.read(2))[0]
            lang_count = 6 if version == 1 else (7 if version == 2 else 8)
            banner_size = 0x840 if version == 1 else (0x940 if version == 2 else 0xA40)

            encoded_text = new_banner_text.encode("utf-16-le")
            if len(encoded_text) > 254:
                err_node = ET.SubElement(error_root, "File", name=filename)
                ET.SubElement(err_node, "Reason").text = f"文本过长 ({len(encoded_text)} bytes)"
                return False, "文本过长"

            f.seek(banner_offset)
            banner_data = bytearray(f.read(banner_size))
            for i in range(lang_count):
                start_pos = 0x240 + (i * 256)
                banner_data[start_pos : start_pos+256] = b'\x00' * 256
                banner_data[start_pos : start_pos+len(encoded_text)] = encoded_text

            banner_data[0x02], banner_data[0x03] = 0, 0
            new_crc = calc_crc16(banner_data[0x20:])
            struct.pack_into("<H", banner_data, 0x02, new_crc)

            f.seek(banner_offset)
            f.write(banner_data)
            return True, "成功"
    except Exception as e:
        return False, str(e)

# --- 标题清洗 ---
def clean_game_title(title):
    pattern = r'\s*(?:[vV]\d+[\d\.]*|\d+\.\d+|[0-9]*精修版|完全汉化版|汉化版|大字库版|最终版|完美版|英文字幕|中文字幕|中文配音|汉语配音).*$'
    return re.sub(pattern, '', title, flags=re.IGNORECASE).strip()

# --- 文件名解析 (已修复 Mb 小数点和增加地区) ---
def parse_filename(filename):
    # 统一括号
    norm_name = filename.replace('（', '(').replace('）', ')')
    if norm_name.lower().endswith('.nds'): norm_name = norm_name[:-4]
    
    match = re.match(r'^(.*?)((\([^)]*\))+)$', norm_name)
    raw_title = match.group(1).strip() if match else norm_name.strip()
    tags = re.findall(r'\(([^)]*)\)', match.group(2)) if match else []

    clean_title = clean_game_title(raw_title)

    # 扩展地区白名单：增加了 EU, HB, ASIA 等
    valid_regions = {
        'US', 'JP', 'FR', 'DE', 'ES', 'IT', 'NL', 'PT', 'RU', 'KO', 
        'ZHCN', 'ZHTW', 'EU', 'HB', 'ASIA', 'UK', 'CN'
    }
    
    region, trans_group = "", ""
    for tag in tags:
        tag_upper = tag.upper().strip()
        # 修复：正则改为匹配包含小数点的 Mb 格式
        if tag_upper in ['简', '繁'] or re.match(r'^[\d.]+MB$', tag_upper):
            continue
        elif tag_upper in valid_regions:
            region = tag_upper
        else:
            if not trans_group: trans_group = tag.strip()
            else: trans_group += f" & {tag.strip()}"

    return clean_title, region, trans_group

# --- 模式1：自动批量处理 ---
def auto_process_folder(folder_path):
    error_root = ET.Element("ErrorLog")
    errors_found = False
    print(f"\n[自动模式] 正在扫描文件夹: {folder_path} ...")

    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(".nds"): continue

        clean_title, region, trans_group = parse_filename(filename)
        line2 = ""
        if trans_group and region: line2 = f"{trans_group}({region})"
        elif trans_group: line2 = trans_group
        elif region: line2 = f"({region})"
            
        new_banner_text = f"{clean_title}\n{line2}" if line2 else clean_title
        new_banner_text = new_banner_text.replace('（', '(').replace('）', ')')

        success, msg = apply_banner_update(os.path.join(folder_path, filename), filename, new_banner_text, error_root)
        if success:
            print(f"[成功] {filename}")
        else:
            errors_found = True
            print(f"[跳过] {filename} -> {msg}")

    if errors_found:
        save_xml(error_root, os.path.join(folder_path, "auto_errors.xml"))
        print(f"\n任务完成。发现部分错误，详情请查看 auto_errors.xml")
    else:
        print(f"\n任务完美完成！没有产生错误。")

# --- 模式2：手动逐个编辑 ---
def manual_process_folder(folder_path):
    error_root = ET.Element("ErrorLog")
    errors_found = False
    
    # 筛选并按首字母排序
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(".nds")]
    files.sort(key=lambda x: x.lower())

    if not files:
        print("\n未找到任何 .nds 文件！")
        return

    print(f"\n[手动模式] 共找到 {len(files)} 个文件。准备开始...")
    print("提示：在要求输入【第一行】时，直接按回车(Enter)将跳过当前文件。\n")

    for index, filename in enumerate(files, 1):
        print("-" * 50)
        print(f"[{index}/{len(files)}] 当前文件: {filename}")
        
        line1 = input("请输入第一行内容 (游戏标题) [回车跳过]: ").strip()
        if not line1:
            print(">> 已跳过。")
            continue
            
        line2 = input("请输入第二行内容 (汉化组等) [回车留空]: ").strip()
        
        # 组装文本
        new_banner_text = f"{line1}\n{line2}" if line2 else line1
        
        # 应用修改
        file_path = os.path.join(folder_path, filename)
        success, msg = apply_banner_update(file_path, filename, new_banner_text, error_root)
        
        if success:
            print(f">> [成功] 横幅已更新！")
        else:
            errors_found = True
            print(f">> [失败] {msg}")

    if errors_found:
        save_xml(error_root, os.path.join(folder_path, "manual_errors.xml"))
        print(f"\n编辑结束。部分文件由于字数限制等原因修改失败，详情请查看 manual_errors.xml")
    else:
        print(f"\n编辑结束，全部操作均顺利完成！")

# --- 启动菜单 ---
if __name__ == "__main__":
    print("=============================")
    print("    NDS Banner 编辑工具集")
    print("=============================")
    print("1. 自动匹配修改 (根据文件名批量处理)")
    print("2. 手动逐个编辑 (依次输入横幅内容)")
    print("=============================")
    
    choice = input("请选择工作模式 (1 或 2): ").strip()
    if choice not in ['1', '2']:
        print("无效选项，已退出。")
        exit()
        
    target_dir = input("请输入包含 .nds 文件的文件夹路径: ").strip('"')
    if os.path.isdir(target_dir):
        if choice == '1':
            auto_process_folder(target_dir)
        else:
            manual_process_folder(target_dir)
    else:
        print("无效的文件夹路径。")