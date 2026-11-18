import datetime
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}


def fetch_bytes(url, timeout=20):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_text(url, timeout=20):
    return fetch_bytes(url, timeout=timeout).decode("utf-8", errors="ignore")


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


def find_averdade_cover_url(html):
    # 1. Look for images mentioning edicao / capa / jornal / pagina-1 / primeira-pagina in src or alt
    img_tags = re.findall(r"<img[^>]+>", html, re.I)
    for tag in img_tags:
        src_m = re.search(r'(?:data-src|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp))[^"\']*["\']', tag, re.I)
        if not src_m:
            continue
        src = src_m.group(1)
        if any(k in tag.lower() for k in ["edicao", "edição", "capa", "primeira-pagina", "jornal-a-verdade", "impresso"]):
            # Prefer full-size over tiny thumbnails
            clean_src = re.sub(r"-\d+x\d+(?=\.(?:jpg|jpeg|png|webp)$)", "", src, flags=re.I)
            return clean_src

    # 2. Look for links to /edicoes/ or /edicao- and inspect that page
    ed_link = re.search(r'href=["\'](https?://averdade\.org\.br/[^"\']*edica[o|ões][^"\']*)["\']', html, re.I)
    if ed_link:
        try:
            ed_html = fetch_text(ed_link.group(1))
            og_ed = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', ed_html, re.I)
            if og_ed:
                return og_ed.group(1)
        except Exception:
            pass

    # 3. Fallback to homepage og:image
    og_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if og_img:
        return og_img.group(1)
    return ""


def fetch_averdade():
    local_rel_path = "img/capa-a-verdade.jpg"
    os.makedirs("img", exist_ok=True)
    capa = {
        "titulo": "Jornal A Verdade — Edição Semanal",
        "descricao": "Capa da edição impressa atualizada semanalmente direto do portal oficial.",
        "url": "https://averdade.org.br/",
        "imagem": local_rel_path if os.path.exists(local_rel_path) else "",
        "origem_url": ""
    }
    try:
        html = fetch_text("https://averdade.org.br/")
        ed_match = re.search(r"Edi[çc][ãa]o\s*(?:n[º°]?\s*)?(\d{2,4})", html, re.I)
        if ed_match:
            capa["titulo"] = f"Jornal A Verdade — Edição nº {ed_match.group(1)}"

        ed_href = re.search(r'href=["\'](https?://averdade\.org\.br/[^"\']*edica[^"\']*)["\']', html, re.I)
        if ed_href:
            capa["url"] = ed_href.group(1)

        img_url = find_averdade_cover_url(html)
        if img_url:
            full_img_url = urllib.parse.urljoin("https://averdade.org.br/", img_url)
            capa["origem_url"] = full_img_url
            img_bytes = fetch_bytes(full_img_url)
            if len(img_bytes) > 4000:
                with open(local_rel_path, "wb") as f:
                    f.write(img_bytes)
                capa["imagem"] = local_rel_path
                print(f"Capa salva localmente em {local_rel_path} ({len(img_bytes)} bytes).")
    except Exception as exc:
        print(f"Aviso ao baixar capa do A Verdade: {exc}")
    return capa


def main():
    manchetes = []
    manchetes.extend(parse_rss("https://iclnoticias.com.br/feed/", "ICL Notícias", limit=3))
    manchetes.extend(parse_rss("https://www.brasildefato.com.br/feed/", "Brasil de Fato", limit=3))
    manchetes.extend(parse_rss("https://averdade.org.br/feed/", "Jornal A Verdade", limit=2))

    capa = fetch_averdade()

    if not manchetes and not capa.get("imagem"):
        print("Nenhuma atualização coletada; mantendo arquivos anteriores.")
        return

    os.makedirs("data", exist_ok=True)
    payload = {
        "atualizado_em": datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "capa_averdade": capa,
        "manchetes": manchetes
    }
    with open("data/noticias.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Atualizado com {len(manchetes)} manchetes e capa: {capa.get('imagem')}.")


if __name__ == "__main__":
    main()
