<img src="./serverless_handler/static/favicon.png" alt="Logo" width="100"/>

# PDF 彩色和黑白页面分离器

此工具用于将 PDF 文件中的彩色页面和黑白页面分离成两个独立的 PDF 文件。提供基于 Docker 的一键部署方式和浏览器操作界面。

## 快速开始（Docker）

### 方式一：Docker Compose（推荐）

```bash
docker compose up --build
```

启动后在浏览器中访问 **http://localhost:9000**。

### 方式二：纯 Docker 命令

```bash
# 构建镜像
docker build -t pdf-separator .

# 运行容器（结果文件会保存到宿主机 ./data 目录）
docker run -p 9000:9000 -v "$(pwd)/data:/data" pdf-separator
```

启动后在浏览器中访问 **http://localhost:9000**。

## 使用步骤

1. **上传文件** – 选择需要处理的 PDF 文件（最大支持 512 MB），点击 *上传文件*。
2. **处理文件** – 根据需要调整参数，点击 *开始处理*，进度条实时显示处理进度。
3. **下载文件** – 处理完成后，点击下载按钮将彩色或黑白 PDF 保存到本地。

## 持久化存储

处理后的文件保存在容器内：

| 路径 | 内容 |
|------|------|
| `/data/input/` | 上传的 PDF（处理完成后自动删除） |
| `/data/output/` | 分离结果（`{session}_color.pdf`、`{session}_bw.pdf`） |

使用卷挂载（`-v ./data:/data`）时，所有输出文件会持久化到宿主机 `./data/output/` 目录。

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 双面打印模式 | ✓ | 将与彩色页面相邻的页面也视为彩色，适用于双面打印场景 |
| 饱和度阈值 | 0.35 | 越小则越多页面被判定为彩色 |
| 色彩比例阈值 | 0.001 | 越小则越多页面被判定为彩色 |

## 不使用 Docker 的运行方式

```bash
pip install -r requirements.txt
python serverless_handler/ws_server.py
```

服务默认监听 `http://0.0.0.0:9000`。可通过环境变量 `DATA_DIR` 指定数据目录。

## 贡献

欢迎贡献！如果你发现任何问题或有任何建议，请提出 issue。如果你想贡献代码，请 fork 此仓库并提交 pull request。

## 许可证

此项目使用 MIT 许可证。更多详情请参见 [LICENSE](LICENSE) 文件。

