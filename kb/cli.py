"""CLI interface for KB."""
from __future__ import annotations

# Suppress warnings before any imports
import warnings
warnings.filterwarnings("ignore")

import asyncio
import sys
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import load_config, get_config_path, Config
from .llm import create_llm, BaseLLM
from .processors import detect_and_process, extract_urls, ProcessedContent, UnsupportedFileError
from .tagger import Tagger
from .publisher import TelegramPublisher


console = Console()


# ASCII Art Logo - Gemini style: Blue → Purple → Pink gradient
LOGO = """
[bold #4a9ced]   ██████╗  [/][bold #6b8cdf]      ██████╗[/][bold #8a7ecf]  █████╗ ██[/][bold #b06ebf]████╗ ██╗  [/][bold #e36eaa]    ██████╗[/]
[bold #4a9ced]  ██╔═████╗ [/][bold #6b8cdf]      ██╔══██[/][bold #8a7ecf]╗██╔══██╗██[/][bold #b06ebf]╔══██╗██║  [/][bold #e36eaa]   ██╔═══██╗[/]
[bold #4a9ced]  ██║██╔██║ [/][bold #6b8cdf]██╗██╗██████╔[/][bold #8a7ecf]╝███████║██[/][bold #b06ebf]████╔╝██║  [/][bold #e36eaa]   ██║   ██║[/]
[bold #4a9ced]  ████╔╝██║ [/][bold #6b8cdf]╚███╔╝██╔═══╝[/][bold #8a7ecf] ██╔══██║██[/][bold #b06ebf]╔══██╗██║  [/][bold #e36eaa]   ██║   ██║[/]
[bold #4a9ced]  ╚██████╔╝ [/][bold #6b8cdf]██╔██╗██║    [/][bold #8a7ecf] ██║  ██║██[/][bold #b06ebf]████╔╝█████[/][bold #e36eaa]██╗╚██████╔╝[/]
[bold #4a9ced]   ╚═════╝  [/][bold #6b8cdf]╚═╝╚═╝╚═╝    [/][bold #8a7ecf] ╚═╝  ╚═╝╚═[/][bold #b06ebf]════╝ ╚════[/][bold #e36eaa]══╝ ╚═════╝[/]

[bold #4a9ced]  ██╗  ██╗[/][bold #8a7ecf]██████╗[/]   [dim]Knowledge Base v0.1.0[/dim]
[bold #4a9ced]  ██║ ██╔╝[/][bold #8a7ecf]██╔══██╗[/]  [dim]Telegram Channel Publisher[/dim]
[bold #4a9ced]  █████╔╝ [/][bold #8a7ecf]██████╔╝[/]
[bold #4a9ced]  ██╔═██╗ [/][bold #8a7ecf]██╔══██╗[/]
[bold #4a9ced]  ██║  ██╗[/][bold #8a7ecf]██████╔╝[/]
[bold #4a9ced]  ╚═╝  ╚═╝[/][bold #8a7ecf]╚═════╝[/]
"""


def get_history_path() -> str:
    """Get path for command history."""
    return str(get_config_path().parent / "history")


class KBApp:
    """Main KB CLI application."""

    def __init__(self):
        self.config: Optional[Config] = None
        self.llm: Optional[BaseLLM] = None
        self.tagger: Optional[Tagger] = None
        self.publisher: Optional[TelegramPublisher] = None
        self.session: Optional[PromptSession] = None

    def initialize(self) -> bool:
        """Initialize the application."""
        try:
            self.config = load_config()
        except Exception as e:
            console.print(f"[red]配置加载失败: {e}[/red]")
            return False

        # Initialize LLM
        try:
            self.llm = create_llm(self.config)
        except ValueError as e:
            console.print(f"[yellow]⚠ LLM: {e}[/yellow]")
            self.llm = None

        # Initialize tagger
        self.tagger = Tagger(self.config, self.llm)

        # Initialize publisher
        if self.config.telegram.bot_token and self.config.telegram.channel_id:
            self.publisher = TelegramPublisher(self.config)
        else:
            console.print("[yellow]⚠ Telegram 未配置[/yellow]")

        # Initialize prompt session
        self.session = PromptSession(
            history=FileHistory(get_history_path()),
            auto_suggest=AutoSuggestFromHistory(),
        )

        return True

    def show_welcome(self):
        """Show welcome screen."""
        console.print(LOGO)

        # Status line
        status_parts = []
        if self.llm:
            status_parts.append(f"[green]● LLM: {self.config.llm.default_provider}[/green]")
        else:
            status_parts.append("[red]○ LLM: 未配置[/red]")

        if self.publisher:
            status_parts.append(f"[green]● Channel: {self.config.telegram.channel_id}[/green]")
        else:
            status_parts.append("[red]○ Channel: 未配置[/red]")

        console.print("  " + "  ".join(status_parts))
        console.print()

        # Show preset tags
        if self.tagger.preset_tags:
            tags_display = " ".join(f"[dim]#{tag}[/dim]" for tag in self.tagger.preset_tags[:10])
            if len(self.tagger.preset_tags) > 10:
                tags_display += f" [dim]+{len(self.tagger.preset_tags) - 10} more[/dim]"
            console.print(f"  [bold]预设Tags:[/bold] {tags_display}")
            console.print()

    async def prompt_async(self, message: str, default: str = "") -> str:
        """Async prompt wrapper."""
        return await self.session.prompt_async(message, default=default)

    async def run_interactive(self):
        """Run the interactive CLI loop."""
        self.show_welcome()

        while True:
            try:
                console.print("[bold green]▶[/bold green] [bold]有什么想收藏的？[/bold] [dim](q 退出)[/dim]")
                user_input = await self.prompt_async("  ")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ("q", "quit", "exit"):
                    console.print("[dim]再见！👋[/dim]")
                    break

                # Check for multiple URLs
                urls = extract_urls(user_input)

                if len(urls) > 1:
                    await self.handle_multiple_urls(user_input, urls)
                else:
                    await self.process_input(user_input)

                console.print()

            except KeyboardInterrupt:
                console.print("\n[dim]Ctrl+C 退出[/dim]")
                continue
            except EOFError:
                break

    async def handle_multiple_urls(self, original_input: str, urls: list[str]):
        """Handle input containing multiple URLs."""
        console.print()
        console.print(f"[yellow]检测到 {len(urls)} 个链接：[/yellow]")
        for i, url in enumerate(urls, 1):
            console.print(f"  [dim]{i}.[/dim] {url[:60]}{'...' if len(url) > 60 else ''}")

        console.print()
        console.print("[bold]如何处理？[/bold]")
        console.print("  [cyan]1[/cyan] 合并为一条消息")
        console.print("  [cyan]2[/cyan] 分别发布多条消息")
        console.print("  [cyan]3[/cyan] 取消")

        choice = await self.prompt_async("  选择 (1/2/3): ", default="1")
        choice = choice.strip()

        if choice == "1":
            # Process as single message with all URLs
            await self.process_input(original_input)
        elif choice == "2":
            # Process each URL separately
            for i, url in enumerate(urls, 1):
                console.print(f"\n[bold cyan]处理链接 {i}/{len(urls)}[/bold cyan]")
                await self.process_input(url)
                if i < len(urls):
                    cont = await self.prompt_async("继续下一个？(Y/n): ", default="y")
                    if cont.strip().lower() not in ("", "y", "yes"):
                        console.print("[dim]已停止[/dim]")
                        break
        else:
            console.print("[dim]已取消[/dim]")

    async def process_input(self, user_input: str):
        """Process a single input."""
        console.print()

        with console.status("[bold blue]正在解析...[/bold blue]"):
            try:
                content = await detect_and_process(user_input)
            except UnsupportedFileError as e:
                console.print(f"[red]✗ {e}[/red]")
                console.print("[dim]提示: 目前只支持 PDF 和图片文件[/dim]")
                return
            except Exception as e:
                console.print(f"[red]✗ 解析失败: {e}[/red]")
                return

        # Generate bilingual summary
        summary_failed = False
        original_title = content.title  # Save original title for translation
        if self.llm and content.content:
            with console.status("[bold blue]正在生成双语摘要...[/bold blue]"):
                try:
                    bilingual = await self.llm.summarize_bilingual(
                        content.content,
                        original_title=original_title
                    )
                    if bilingual.get("title_cn"):
                        content.title = bilingual["title_cn"]
                    content.summary = bilingual.get("summary_cn", "")
                    content.title_en = bilingual.get("title_en") or original_title
                    content.summary_en = bilingual.get("summary_en", "")
                except Exception as e:
                    summary_failed = True
                    console.print(f"[yellow]⚠ 摘要失败: {e}[/yellow]")

        self._display_preview(content)

        # Get tag suggestions
        suggested_tags = []
        extra_tags = []

        # If content available and summary succeeded, use full content for tags
        if self.llm and content.content and not summary_failed:
            with console.status("[bold blue]正在分析标签...[/bold blue]"):
                try:
                    suggested_tags = await self.tagger.suggest_tags(content.content)
                    extra_tags = await self.tagger.generate_extra_tags(content.content)
                except Exception:
                    pass

        # Fallback: generate tags from title if no tags yet
        if self.llm and not suggested_tags:
            with console.status("[bold blue]根据标题生成标签...[/bold blue]"):
                try:
                    suggested_tags, extra_tags = await self.tagger.generate_tags_from_title(
                        content.title, content.source
                    )
                except Exception:
                    pass

        # Show tag selection interface
        console.print()
        self._display_tag_selection(suggested_tags, extra_tags)

        all_suggested = suggested_tags + extra_tags
        tag_input = await self.prompt_async(
            "  输入tags (空格分隔): ",
            default=" ".join(all_suggested) if all_suggested else "",
        )
        tag_input = tag_input.strip()

        if tag_input:
            user_tags = self.tagger.parse_user_input(tag_input)
            content.tags = self.tagger.process_tags(user_tags)
        else:
            content.tags = all_suggested

        if not self.publisher:
            console.print("[yellow]⚠ Telegram 未配置，无法发布[/yellow]")
            self._show_formatted_output(content)
            return

        console.print()
        confirm = await self.prompt_async("  确认发布？(Y/n): ", default="y")
        confirm = confirm.strip().lower()

        if confirm in ("", "y", "yes"):
            with console.status("[bold blue]正在发布...[/bold blue]"):
                try:
                    url = await self.publisher.publish(content)
                    console.print("[bold green]✓ 已发布！[/bold green]")
                    console.print(f"  [dim]{url}[/dim]")
                except Exception as e:
                    console.print(f"[red]✗ 发布失败: {e}[/red]")
        else:
            console.print("[dim]已取消[/dim]")

    def _display_preview(self, content: ProcessedContent):
        """Display content preview in bilingual format."""
        lines = []

        # Chinese section
        lines.append(f"[bold cyan]📌 {content.title}[/bold cyan]")
        if content.summary:
            lines.append(f"[dim]📝 {content.summary}[/dim]")

        if content.source and content.source != "text":
            lines.append(f"[dim]🔗 {content.source}[/dim]")

        # Separator
        lines.append("")
        lines.append("[dim]─" * 30 + "[/dim]")
        lines.append("")

        # English section
        en_title = content.title_en or content.title
        lines.append(f"[bold cyan]📌 {en_title}[/bold cyan]")
        if content.summary_en:
            lines.append(f"[dim]📝 {content.summary_en}[/dim]")
        elif content.summary:
            lines.append(f"[dim]📝 {content.summary}[/dim]")

        if content.source and content.source != "text":
            lines.append(f"[dim]🔗 {content.source}[/dim]")

        panel = Panel(
            "\n".join(lines),
            border_style="blue",
            padding=(0, 1),
            title="[bold]预览 Preview[/bold]",
            title_align="left",
        )
        console.print(panel)

    def _display_tag_selection(self, suggested: list[str], extra: list[str]):
        """Display tag selection interface."""
        console.print("[bold]🏷️  标签[/bold]")

        # Preset tags
        preset_display = []
        for tag in self.tagger.preset_tags:
            if tag in suggested:
                preset_display.append(f"[bold green][{tag}][/bold green]")
            else:
                preset_display.append(f"[dim]{tag}[/dim]")
        console.print(f"  预设: {' '.join(preset_display)}")

        # LLM generated extra tags
        if extra:
            extra_display = " ".join(f"[cyan]+{tag}[/cyan]" for tag in extra)
            console.print(f"  新增: {extra_display}")

        console.print()

    def _show_formatted_output(self, content: ProcessedContent):
        """Show the formatted output."""
        console.print()
        console.print("[bold]预览输出:[/bold]")
        console.print(Panel(content.format_for_telegram(), border_style="dim"))


def main():
    """Main entry point."""
    app = KBApp()

    if not app.initialize():
        console.print()
        console.print("[bold]首次使用请配置:[/bold]")
        console.print(f"  编辑 [cyan]{get_config_path()}[/cyan] 或项目目录下的 [cyan].env[/cyan]")
        sys.exit(1)

    try:
        asyncio.run(app.run_interactive())
    except KeyboardInterrupt:
        console.print("\n[dim]再见！[/dim]")


if __name__ == "__main__":
    main()
