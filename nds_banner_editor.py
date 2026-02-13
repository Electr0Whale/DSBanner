import os
import struct
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- CRC16 算法 (NDS Banner 专用) ---
def calc_crc16(data):
    """计算 NDS Banner 的 CRC16 (Polynomial 0xA001)"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

# --- XML 格式化工具 ---
def save_xml(root, filename):
    xml_str = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent="  ")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(xml_str)

# --- 主逻辑 ---
def process_nds_folder(folder_path):
    # 正则表达式：匹配 游戏名(地区)(汉化组)(大小).nds
    # group(1)=游戏名, group(2)=地区, group(3)=汉化组, group(4)=大小
    filename_pattern = re.compile(r"^(.*?)\((.*?)\)\((.*?)\)\((.*?)\)\.nds$", re.IGNORECASE)

    # 准备 XML 错误日志
    error_root = ET.Element("ErrorLog")
    errors_found = False

    print(f"正在扫描文件夹: {folder_path} ...")

    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(".nds"):
            continue

        file_path = os.path.join(folder_path, filename)
        
        # 1. 解析文件名
        match = filename_pattern.match(filename)
        if not match:
            # 记录文件名格式错误
            err_node = ET.SubElement(error_root, "File", name=filename)
            ET.SubElement(err_node, "Reason").text = "文件名格式不匹配，无法提取汉化组信息"
            errors_found = True
            print(f"[跳过] 格式不符: {filename}")
            continue

        game_name = match.group(1).strip()
        trans_group = match.group(3).strip()
        
        # 构造新的横幅文字 (第一行游戏名 \n 第二行汉化组)
        new_banner_text = f"{game_name}\n{trans_group}"

        try:
            with open(file_path, "r+b") as f:
                # 2. 读取 Banner 偏移量 (Header 0x68)
                f.seek(0x68)
                banner_offset = struct.unpack("<I", f.read(4))[0]

                if banner_offset == 0:
                    raise ValueError("ROM Header 中未找到 Banner 偏移量")

                # 3. 读取 Banner 版本以确定大小和语言数
                f.seek(banner_offset)
                version = struct.unpack("<H", f.read(2))[0]
                
                # 确定语言数量和校验范围
                # V1 (0x0001): 6 语言, 大小 0x840
                # V2 (0x0002): 7 语言, 大小 0x940
                # V3 (0x0003+): 8 语言, 大小 0xA40 (基础部分)
                if version == 1:
                    lang_count = 6
                    banner_size = 0x840
                elif version == 2:
                    lang_count = 7
                    banner_size = 0x940
                else: # version >= 3
                    lang_count = 8
                    banner_size = 0xA40 

                # 4. 预检查：编码后是否会溢出？
                # NDS 标题最大 256 字节 (UTF-16LE)，包括结束符
                encoded_text = new_banner_text.encode("utf-16-le")
                # 必须保留至少2字节给 \0\0
                if len(encoded_text) > 254:
                    # 读取原始标题用于记录日志
                    f.seek(banner_offset + 0x240) # 读取第一个语言(日语)作为参考
                    raw_orig = f.read(256)
                    orig_title = raw_orig.split(b'\x00\x00')[0].decode("utf-16-le", errors="ignore")

                    err_node = ET.SubElement(error_root, "File", name=filename)
                    ET.SubElement(err_node, "OriginalBanner").text = orig_title
                    ET.SubElement(err_node, "IntendedBanner").text = new_banner_text
                    ET.SubElement(err_node, "Reason").text = f"文本过长 (编码后 {len(encoded_text)} 字节 > 上限 254 字节)"
                    errors_found = True
                    print(f"[错误] 文字过长: {filename}")
                    continue

                # 5. 开始修改 (内存操作)
                # 将整个 banner 区块读入内存，修改后再写回，方便计算 CRC
                f.seek(banner_offset)
                banner_data = bytearray(f.read(banner_size))

                # 填充所有语言槽位
                # 标题数据从 banner 偏移 0x240 开始，每个语言 256 字节
                for i in range(lang_count):
                    start_pos = 0x240 + (i * 256)
                    # 清空当前槽位 (填充 0x00)
                    banner_data[start_pos : start_pos+256] = b'\x00' * 256
                    # 写入新数据
                    banner_data[start_pos : start_pos+len(encoded_text)] = encoded_text

                # 6. 重新计算 CRC
                # CRC 位于偏移 0x02，覆盖范围从 0x20 到 Banner 结束
                # 先把 CRC 位置零，虽然计算时不包含它，但为了保险
                banner_data[0x02] = 0x00
                banner_data[0x03] = 0x00

                # 计算范围: [0x20 : end]
                new_crc = calc_crc16(banner_data[0x20:])
                
                # 写入新的 CRC (小端)
                struct.pack_into("<H", banner_data, 0x02, new_crc)

                # 7. 写回文件
                f.seek(banner_offset)
                f.write(banner_data)
                print(f"[成功] 已修改: {filename}")

        except Exception as e:
            err_node = ET.SubElement(error_root, "File", name=filename)
            ET.SubElement(err_node, "OriginalBanner").text = "Read Error"
            ET.SubElement(err_node, "IntendedBanner").text = new_banner_text
            ET.SubElement(err_node, "Reason").text = str(e)
            errors_found = True
            print(f"[失败] 发生异常: {filename} - {str(e)}")

    # 保存错误日志
    if errors_found:
        save_xml(error_root, os.path.join(folder_path, "modification_errors.xml"))
        print(f"\n任务完成。发现部分错误，详情请查看 modification_errors.xml")
    else:
        print(f"\n任务完美完成！没有发现错误。")

# --- 入口 ---
if __name__ == "__main__":
    target_dir = input("请输入包含 .nds 文件的文件夹路径: ").strip('"')
    if os.path.isdir(target_dir):
        process_nds_folder(target_dir)
    else:
        print("无效的文件夹路径。")