import os
import struct
import xml.etree.ElementTree as ET
from xml.dom import minidom

def get_nds_banners(folder_path):
    languages = [
        "Japanese", "English", "French", "German", 
        "Italian", "Spanish", "Korean", "Chinese"
    ]
    
    root = ET.Element("NDSRomList")

    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(".nds"):
            continue
            
        file_path = os.path.join(folder_path, filename)
        rom_node = ET.SubElement(root, "Game", filename=filename)
        
        try:
            with open(file_path, "rb") as f:
                f.seek(0x68)
                banner_offset_raw = f.read(4)
                if not banner_offset_raw: continue
                banner_offset = struct.unpack("<I", banner_offset_raw)[0]
                
                if banner_offset == 0:
                    ET.SubElement(rom_node, "Error").text = "No Banner Data"
                    continue
                
                f.seek(banner_offset)
                version = struct.unpack("<H", f.read(2))[0]
                
                lang_count = 6
                if version == 2: lang_count = 7
                elif version >= 3: lang_count = 8
                
                for i in range(lang_count):
                    f.seek(banner_offset + 0x240 + (i * 256))
                    raw_title = f.read(256)
                    
                    # --- 修复逻辑：寻找 UTF-16 结束符 ---
                    # 我们每 2 个字节检查一次，直到发现 0x0000
                    clean_bytes = bytearray()
                    for j in range(0, 256, 2):
                        char_bytes = raw_title[j:j+2]
                        if char_bytes == b'\x00\x00' or len(char_bytes) < 2:
                            break
                        clean_bytes.extend(char_bytes)
                    
                    # 解码
                    title_str = clean_bytes.decode("utf-16-le", errors="replace").strip()
                    
                    lang_element = ET.SubElement(rom_node, languages[i])
                    lang_element.text = title_str

        except Exception as e:
            ET.SubElement(rom_node, "Error").text = str(e)

    # 导出
    xml_data = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(xml_data)
    with open("banners.xml", "w", encoding="utf-8") as f:
        f.write(reparsed.toprettyxml(indent="  "))
    
    print(f"修正版完成！'Nintendo' 现在应该能完整显示了。")

if __name__ == "__main__":
    target_dir = input("请输入文件夹路径: ").strip('"')
    if os.path.isdir(target_dir):
        get_nds_banners(target_dir)