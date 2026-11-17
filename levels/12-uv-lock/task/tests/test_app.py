from rich.console import Console

import httpx
import requests


def test_http_clients_importable():
    assert requests.__version__ == "2.31.0"
    assert httpx.__version__ == "0.27.2"


def test_rich_console():
    console = Console(record=True, width=40)
    console.print("[bold green]env demo[/bold green]")
    assert "env demo" in console.export_text()
