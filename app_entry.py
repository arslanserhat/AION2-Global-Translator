import json
from pathlib import Path
import sys
from aion2_global_translator.gui import main


def self_check(output):
    """Offline distribution smoke check; no game reads or provider requests."""
    from aion2_global_translator.codec import FString, L10NDocument, L10NTable, locale_seed
    from aion2_global_translator.protection import prepare
    from aion2_global_translator.providers import LibreTranslateProvider
    import tkinter as tk
    table = L10NTable(FString("SYNTHETIC"), [(FString("KEY"), FString("Merhaba ğüşİöç"))])
    doc = L10NDocument(table, "en-US", b"", key=b"k" * 32, prefix=b"p" * 32)
    data = doc.encode()
    result = L10NDocument.decode(data, "en-US", {locale_seed("en-US"): b"k" * 32})
    assert result.table.as_dict() == {"KEY": "Merhaba ğüşİöç"}
    text = "<b>{amount}</> 25%\nText"
    protected = prepare(text)
    assert protected.restore(protected.html) == text
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    root.destroy()
    Path(output).write_text(json.dumps(dict(codec=True, unicode=True, protection=True, tkinter=True,
                                           network_requests=0, game_files_touched=0)), encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-check":
        self_check(sys.argv[2])
    else:
        main()
