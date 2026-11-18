import datetime
import json
import re
import urllib.request
import xml.etree.ElementTree as ET

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PorOndeComecarBot/1.0)"}

def fetch_text(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def parse_rss(url, veiculo, limit=3):
    items = []
    try:
        xml_text = fetch_text(url)
        root = ET.fromstring(xml_text)
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()[:16]
            if title and link:
                items.append({"veiculo": veiculo, "titulo": title, "url": link, "data": pub})
    except Exception as exc:
        print(f"Aviso ao ler RSS de {veiculo}: {exc}")
    return items

def fetch_averdade():
    capa = {
        "titulo": "Jornal A Verdade — Edição Semanal",
        "descricao": "Confira a edição mais recente no portal oficial do Jornal A Verdade.",
        "url": "https://averdade.org.br/",
        "imagem": ""
    }
    try:
        html = fetch_text("https://averdade.org.br/")
        og_img = re.search(r'<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']', html, re.I)
        if og_img:
            capa["imagem"] = og_img.group(1)
    except Exception as exc:
        print(f"Aviso ao ler capa do A Verdade: {exc}")
    return capa

def main():
    manchetes = []
    manchetes.extend(parse_rss("https://iclnoticias.com.br/feed/", "ICL Notícias", limit=3))
    manchetes.extend(parse_rss("https://www.brasildefato.com.br/feed/", "Brasil de Fato", limit=3))
    manchetes.extend(parse_rss("https://averdade.org.br/feed/", "Jornal A Verdade", limit=2))

    if not manchetes:
        print("Nenhuma manchete coletada; mantendo arquivo anterior.")
        return

    payload = {
        "atualizado_em": datetime.datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"),
        "capa_averdade": fetch_averdade(),
        "manchetes": manchetes
    }
    with open("data/noticias.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Atualizado com {len(manchetes)} manchetes.")

if __name__ == "__main__":
    main()
