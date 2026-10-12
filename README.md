# 文件归类整理器

这是一个基于 Python 标准库 Tkinter 的 Windows 图形界面工具，用于按文件名中的共同信息批量整理文件。

## 开源许可证

本项目采用 [GNU General Public License v3.0](LICENSE) 授权，对应 SPDX 标识为 `GPL-3.0-only`。

这是强 Copyleft 许可证：分发本项目的修改版本或基于本项目形成的衍生作品时，必须继续采用 GPLv3，并向接收者提供相应源代码。具体权利和义务以 `LICENSE` 中的完整许可证正文为准。

## 运行

电脑安装 Python 3.9 或更高版本后，双击 `run_file_organizer.bat`，或在 PowerShell 中运行：

```powershell
python .\file_organizer.py
```

不需要安装第三方依赖。

## 示例

对于以下文件：

```text
abc-123456-001.jpg
abc-123456-002.jpg
abc-123456-003.jpg
acb-1234567-001.jpg
acb-1234567-002.jpg
acb-1234567-003.jpg
```

选择源文件夹（目标文件夹可与源文件夹相同），保持默认规则：分隔符 `-`、取第 `2` 段。扫描后会预览两个分组：

```text
123456\
  abc-123456-001.jpg ...
1234567\
  acb-1234567-001.jpg ...
```

点击“开始整理”后执行移动。程序会默认跳过目标目录中的重名文件，也可选择自动改名或覆盖。整理成功后可以使用“撤销上次整理”。

## 自定义规则

- 分隔符模式：用分隔符切分文件名（不含扩展名），按从左到右的段序号取文件夹名。
- 正则模式：填写正则表达式；第 1 个捕获组会作为文件夹名。例如 `^[^-]+-([^-]+)-`。
- 扩展名过滤：填写 `jpg,png,pdf`，留空表示处理全部扩展名。
- 可选递归扫描子文件夹，并可将未匹配文件统一放入“未匹配”文件夹。

## GitHub 自动构建

仓库包含 `.github/workflows/build-windows.yml`。以下操作会自动运行测试并构建 Windows x64 EXE：

- 推送任意分支
- 创建或更新 Pull Request
- 在 GitHub Actions 页面手动运行 `Build Windows EXE`

构建完成后，打开对应的 Actions 运行记录，在 `Artifacts` 区域下载 `FileOrganizer-Windows-x64`。压缩包中包含可独立运行的 `FileOrganizer.exe`，目标电脑不需要安装 Python。Actions artifact 保留 30 天。

当代码推送到 `main` 分支且构建成功后，工作流还会自动创建 `build-<运行编号>` 格式的 Git 标签和 GitHub Release，例如 `build-12`，并将 `FileOrganizer.exe` 作为 Release 附件永久提供下载。PR、其他分支和手动运行不会创建 Release。

## 本地打包为 exe（可选）

如果希望在没有 Python 的电脑上运行，可在已安装 Python 的电脑执行：

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconsole --onefile --name FileOrganizer file_organizer.py
```

生成的 exe 位于 `dist` 文件夹。

## 推送到 GitHub

在 GitHub 创建一个空仓库后，在本目录执行：

```powershell
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```
