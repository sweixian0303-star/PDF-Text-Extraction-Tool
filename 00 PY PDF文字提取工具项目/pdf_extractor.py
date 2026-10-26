import fitz           # PyMuPDF 库，安装时叫 pymupdf，导入时用 fitz
import pytesseract    # 调用 Tesseract OCR 引擎的 Python 接口
from PIL import Image # Pillow 库，用于处理图片（OCR 前需要把 PDF 页面转成图片）
import os             # 内置库，用于检查文件是否存在
import argparse       # 内置库，用于解析命令行参数

# ---- 工具函数 ----

def parse_pages(pages_str, total_pages):
    """把页码字符串解析成 range
    "3"   → range(2, 3)   只取第 3 页
    "1-5" → range(0, 5)   取第 1 到 5 页
    """
    try:
        if "-" in pages_str:                        # 判断是否是范围格式如 "1-5"
            start, end = pages_str.split("-")       # 用 "-" 分割成两个字符串
            start, end = int(start), int(end)       # 转成整数
        else:
            start = end = int(pages_str)            # 单页格式如 "3"，start 和 end 相同

        # 验证页码是否在合法范围内
        if start < 1 or end > total_pages or start > end:
            print(f"❌ 页码超出范围，该 PDF 共 {total_pages} 页")
            return None

        return range(start - 1, end)
        # PDF 页码从 0 开始，用户输入从 1 开始，所以 start - 1
        # 例如用户输入 "1-3" → range(0, 3) → 取索引 0、1、2

    except ValueError:
        # int() 转换失败时抛出 ValueError，说明用户输入了非数字
        print("❌ 页码格式错误，请用数字或 '1-3' 格式")
        return None

def save_text(text, output_path):
    """把提取的文字保存成 txt 文件"""
    with open(output_path, "w", encoding="utf-8") as f:  # utf-8 支持中文和特殊字符
        f.write(text)
    print(f"💾 已保存到：{output_path}")

# ---- 核心功能 ----

def extract_text(pdf_path, pages=None, output=None):
    """从普通 PDF（有文字层）提取文字
    pdf_path：PDF 文件路径
    pages：页码范围字符串，如 "1-5"，None 表示全部页
    output：输出 txt 文件路径，None 表示只打印预览
    """
    if not os.path.exists(pdf_path):
        print(f"❌ 找不到文件：{pdf_path}")
        return None

    doc         = fitz.open(pdf_path)   # 用 fitz 打开 PDF，返回 Document 对象
    total_pages = len(doc)              # 获取总页数
    print(f"📄 文件：{pdf_path}")
    print(f"📖 总页数：{total_pages}")

    # 决定要处理哪些页
    page_range = range(total_pages) if pages is None else parse_pages(pages, total_pages)
    if page_range is None:              # parse_pages 返回 None 表示页码有误
        return None

    all_text = []
    for i in page_range:
        page = doc[i]                   # 用索引取出对应页面，索引从 0 开始
        text = page.get_text()          # 提取该页的文字内容
        all_text.append(f"--- 第 {i+1} 页 ---\n{text}")
        print(f"  ✅ 第 {i+1} 页（{len(text)} 字符）")

    doc.close()                         # 关闭文件，释放内存
    result = "\n".join(all_text)        # 把所有页的文字合并成一个字符串

    if output:
        save_text(result, output)       # 有指定输出路径就保存文件
    else:
        print("\n--- 预览（前 500 字）---")
        print(result[:500])             # 没有指定就打印前 500 字预览

    return result

def search_text(pdf_path, keyword):
    """在 PDF 里搜索关键字，列出所有出现的页码和所在行内容"""
    if not os.path.exists(pdf_path):
        print(f"❌ 找不到文件：{pdf_path}")
        return

    doc     = fitz.open(pdf_path)
    keyword = keyword.lower()           # 转小写，实现大小写不敏感搜索
    found   = []                        # 存放搜索结果：(页码, 所在行) 的列表

    print(f"🔍 搜索关键字：「{keyword}」")
    print(f"📖 共 {len(doc)} 页，搜索中...\n")

    for i, page in enumerate(doc):      # enumerate 同时获取索引 i 和页面对象 page
        text = page.get_text()

        if keyword in text.lower():     # 先快速判断这页有没有关键字，有才进一步处理
            lines = text.split("\n")    # 按换行符分割成行列表
            for line in lines:
                if keyword in line.lower():              # 找到含关键字的行
                    found.append((i + 1, line.strip()))  # strip() 去掉首尾空白
                    # i+1 是因为页码从 1 开始显示

    doc.close()

    if not found:
        print(f"❌ 没有找到「{keyword}」")
        return

    print(f"✅ 共找到 {len(found)} 处：\n")
    for page_num, line in found:        # 解包元组，分别取页码和行内容
        print(f"  第 {page_num} 页：{line}")

def ocr_pdf(pdf_path, output=None):
    """用 OCR 识别扫描版 PDF（图片型，没有文字层）
    流程：PDF 页面 → 图片 → Tesseract 识别 → 文字
    """
    # 指定 Tesseract 可执行文件的路径，Windows 默认安装在这里
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    if not os.path.exists(pdf_path):
        print(f"❌ 找不到文件：{pdf_path}")
        return None

    doc         = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"📄 文件：{pdf_path}")
    print(f"📖 总页数：{total_pages}")
    print(f"🔍 开始 OCR 识别（扫描版较慢，请耐心等待）\n")

    all_text = []

    for i, page in enumerate(doc):
        # fitz.Matrix(2, 2) 表示放大 2 倍渲染，分辨率更高，OCR 更准确
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)   # 把 PDF 页面渲染成像素图

        # pix.samples 是原始 RGB 字节数据，frombytes 把它转成 Pillow Image 对象
        # Tesseract 需要 Pillow Image 格式才能处理
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # image_to_string 调用 Tesseract 识别图片里的文字
        # lang="eng" 指定英文识别，如果要中文改成 "chi_sim"
        text = pytesseract.image_to_string(img, lang="eng")

        all_text.append(f"--- 第 {i+1} 页 ---\n{text}")
        print(f"  ✅ 第 {i+1}/{total_pages} 页完成（{len(text)} 字符）")

    doc.close()
    result = "\n".join(all_text)

    if output:
        save_text(result, output)
    else:
        print("\n--- 预览（前 500 字）---")
        print(result[:500])

    return result

# ---- 命令行接口 ----

def main():
    parser     = argparse.ArgumentParser(description="📄 PDF 文字提取工具")
    subparsers = parser.add_subparsers(dest="command")
    # dest="command" 让解析结果存在 args.command，方便后面判断用了哪个子命令

    # ocr 子命令：python pdf_extractor.py ocr scan.pdf --output result.txt
    ocr_parser = subparsers.add_parser("ocr", help="OCR 识别扫描版 PDF")
    ocr_parser.add_argument("pdf",                    help="PDF 文件路径")
    ocr_parser.add_argument("--output", default=None, help="保存路径，如 result.txt")

    # extract 子命令：python pdf_extractor.py extract report.pdf --pages 1-5
    ext_parser = subparsers.add_parser("extract", help="提取普通 PDF 文字")
    ext_parser.add_argument("pdf",                    help="PDF 文件路径")
    ext_parser.add_argument("--pages",  default=None, help="页码范围，如 1-5 或 3")
    ext_parser.add_argument("--output", default=None, help="保存路径，如 result.txt")

    # search 子命令：python pdf_extractor.py search report.pdf "keyword"
    search_parser = subparsers.add_parser("search", help="搜索关键字")
    search_parser.add_argument("pdf",     help="PDF 文件路径")
    search_parser.add_argument("keyword", help="要搜索的关键字")

    args = parser.parse_args()          # 解析用户实际输入的参数

    if args.command == "extract":
        extract_text(args.pdf, pages=args.pages, output=args.output)
    elif args.command == "search":
        search_text(args.pdf, args.keyword)
    elif args.command == "ocr":
        ocr_pdf(args.pdf, output=args.output)
    else:
        parser.print_help()             # 没有输入子命令时显示帮助信息

# 只有直接运行 pdf_extractor.py 时才执行 main()
# 被其他文件 import 时不会自动执行
if __name__ == "__main__":
    main()