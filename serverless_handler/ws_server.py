#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import base64
import uuid
import numpy as np
from io import BytesIO
from PIL import Image
import fitz
from aiohttp import web, WSMsgType
import pathlib

# 数据目录（可通过环境变量覆盖，默认 /data）
DATA_DIR = os.environ.get("DATA_DIR", "/data")
INPUT_DIR = os.path.join(DATA_DIR, "input")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")

# WebSocket 消息大小上限（100 MB）
MAX_MESSAGE_SIZE = 100 * 1024 * 1024


def ensure_dirs():
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# 判断是否为彩色图像
def is_color_image(image, saturation_threshold=0.35, color_fraction_threshold=0.001):
    image = image.convert('RGB')
    pixels = np.array(image) / 255.0
    max_rgb = np.max(pixels, axis=2)
    min_rgb = np.min(pixels, axis=2)
    delta = max_rgb - min_rgb
    saturation = delta / (max_rgb + 1e-7)
    color_pixels = saturation > saturation_threshold
    color_fraction = np.mean(color_pixels)
    return color_fraction > color_fraction_threshold


# 判断页面是否为彩色
def is_color_page(page, saturation_threshold=0.35, color_fraction_threshold=0.001):
    pix = page.get_pixmap()
    img = pix.tobytes("png")
    image = Image.open(BytesIO(img))
    return is_color_image(image, saturation_threshold, color_fraction_threshold)


# 分割 PDF，结果保存到本地 OUTPUT_DIR
async def split_pdf(input_pdf_path, session_id, is_double_sized_printing,
                    saturation_threshold=0.35, color_fraction_threshold=0.001, websocket=None):
    doc = fitz.open(input_pdf_path)
    color_doc = fitz.open()
    bw_doc = fitz.open()
    color_pages = []
    bw_pages = []
    total_pages = len(doc)

    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        if is_color_page(page, saturation_threshold, color_fraction_threshold):
            color_pages.append(page_num)
        if websocket:
            progress = {
                "type": "progress",
                "current": page_num + 1,
                "total": total_pages,
                "percentage": (page_num + 1) / total_pages * 100
            }
            await websocket.send_json(progress)
            await asyncio.sleep(0.01)

    if is_double_sized_printing:
        additional = []
        for page_num in color_pages:
            if page_num % 2 == 0 and page_num + 1 < total_pages and page_num + 1 not in color_pages:
                additional.append(page_num + 1)
            if page_num % 2 == 1 and page_num - 1 >= 0 and page_num - 1 not in color_pages:
                additional.append(page_num - 1)
        color_pages.extend(additional)
        color_pages = sorted(set(color_pages))

    for i in range(total_pages):
        if i not in color_pages:
            bw_pages.append(i)

    for page_num in sorted(color_pages):
        color_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    for page_num in sorted(bw_pages):
        bw_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

    color_download_url = None
    bw_download_url = None

    if color_pages:
        color_filename = f"{session_id}_color.pdf"
        color_doc.save(os.path.join(OUTPUT_DIR, color_filename), garbage=4, deflate=True)
        color_download_url = f"/files/{color_filename}"

    if bw_pages:
        bw_filename = f"{session_id}_bw.pdf"
        bw_doc.save(os.path.join(OUTPUT_DIR, bw_filename), garbage=4, deflate=True)
        bw_download_url = f"/files/{bw_filename}"

    doc.close()
    color_doc.close()
    bw_doc.close()

    return {
        "color_pdf_url": color_download_url,
        "bw_pdf_url": bw_download_url,
        "color_pages_count": len(color_pages),
        "bw_pages_count": len(bw_pages),
        "total_pages": total_pages
    }


# WebSocket 处理函数
async def websocket_handler(request):
    ws = web.WebSocketResponse(max_msg_size=MAX_MESSAGE_SIZE)
    await ws.prepare(request)

    session_id = str(uuid.uuid4())
    client_files = {}
    chunk_buffers = {}

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    msg_type = data.get("type", "")

                    if msg_type == "upload":
                        file_name = data.get("fileName", "document.pdf")
                        chunk_index = data.get("chunkIndex")
                        total_chunks = data.get("totalChunks")
                        is_last_chunk = data.get("isLastChunk", False)

                        if chunk_index is not None and total_chunks is not None:
                            file_data = data.get("data", "").split(",")[1]
                            if file_name not in chunk_buffers:
                                chunk_buffers[file_name] = [None] * total_chunks
                            chunk_buffers[file_name][chunk_index] = file_data
                            if is_last_chunk or all(chunk is not None for chunk in chunk_buffers[file_name]):
                                if not all(chunk is not None for chunk in chunk_buffers[file_name]):
                                    await ws.send_json({
                                        "type": "error",
                                        "message": "文件上传不完整"
                                    })
                                    continue
                                combined = b"".join([base64.b64decode(c) for c in chunk_buffers[file_name]])
                                file_path = os.path.join(INPUT_DIR, f"{session_id}_{file_name}")
                                with open(file_path, "wb") as f:
                                    f.write(combined)
                                client_files["input_pdf"] = file_path
                                del chunk_buffers[file_name]
                                await ws.send_json({
                                    "type": "upload_response",
                                    "status": "success",
                                    "message": f"文件上传成功: {file_name}",
                                    "filename": file_name
                                })
                        else:
                            file_data = data.get("data", "").split(",")[1]
                            file_path = os.path.join(INPUT_DIR, f"{session_id}_{file_name}")
                            decoded = base64.b64decode(file_data)
                            with open(file_path, "wb") as f:
                                f.write(decoded)
                            client_files["input_pdf"] = file_path
                            await ws.send_json({
                                "type": "upload_response",
                                "status": "success",
                                "message": f"文件上传成功: {file_name}",
                                "filename": file_name
                            })

                    elif msg_type == "process":
                        if "input_pdf" not in client_files:
                            await ws.send_json({
                                "type": "error",
                                "message": "请先上传PDF文件"
                            })
                            continue
                        result = await split_pdf(
                            client_files["input_pdf"],
                            session_id,
                            data.get("isDoubleSided", True),
                            float(data.get("saturationThreshold", 0.35)),
                            float(data.get("colorFractionThreshold", 0.001)),
                            ws
                        )
                        client_files["color_pdf_url"] = result["color_pdf_url"]
                        client_files["bw_pdf_url"] = result["bw_pdf_url"]
                        await ws.send_json({
                            "type": "process_complete",
                            "color_pages": result["color_pages_count"],
                            "bw_pages": result["bw_pages_count"],
                            "total_pages": result["total_pages"],
                            "color_pdf_url": result["color_pdf_url"],
                            "bw_pdf_url": result["bw_pdf_url"]
                        })

                    elif msg_type == "download":
                        file_type = data.get("fileType", "")
                        if file_type not in ["color", "bw"]:
                            await ws.send_json({
                                "type": "error",
                                "message": "文件类型必须是 color 或 bw"
                            })
                            continue
                        url_key = f"{file_type}_pdf_url"
                        if url_key in client_files and client_files[url_key]:
                            await ws.send_json({
                                "type": "file_link",
                                "fileType": file_type,
                                "url": client_files[url_key]
                            })
                        else:
                            await ws.send_json({
                                "type": "error",
                                "message": f"{file_type} PDF 未找到"
                            })
                    else:
                        await ws.send_json({
                            "type": "error",
                            "message": f"未知消息类型: {msg_type}"
                        })
                except Exception as e:
                    await ws.send_json({
                        "type": "error",
                        "message": f"内部处理错误: {str(e)}"
                    })
    finally:
        # 仅清理输入临时文件，输出文件保留在 OUTPUT_DIR 供下载
        print(f"清理会话 {session_id} 的临时输入文件")
        if "input_pdf" in client_files and os.path.exists(client_files["input_pdf"]):
            try:
                os.remove(client_files["input_pdf"])
            except Exception as e:
                print(f"删除输入文件失败: {e}")

    return ws


# 文件下载路由：提供 /files/{filename} 供浏览器下载
async def download_handler(request):
    filename = request.match_info.get("filename", "")
    # 防止路径穿越攻击
    if ".." in filename or os.sep in filename:
        raise web.HTTPForbidden()
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise web.HTTPNotFound()
    return web.FileResponse(
        file_path,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# 根路径重定向到 index.html
async def index_handler(request):
    current_dir = pathlib.Path(__file__).parent.resolve()
    return web.FileResponse(current_dir / 'static' / 'index.html')


# 启动服务器
async def main():
    ensure_dirs()

    app = web.Application()

    # 路由注册顺序：具体路由优先于静态路由
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/files/{filename}', download_handler)

    # 静态文件路由（index.html、favicon.png 等）
    current_dir = pathlib.Path(__file__).parent.resolve()
    static_path = current_dir / 'static'
    app.router.add_static('/static', static_path)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 9000)
    await site.start()

    print(f"服务器已启动在 http://0.0.0.0:9000")
    print(f"WebSocket 端点: ws://0.0.0.0:9000/ws")
    print(f"输入目录: {INPUT_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")

    # 保持服务器运行
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
