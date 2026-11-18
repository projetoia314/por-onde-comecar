import datetime
import html as html_lib
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


def clean_html_text(raw):
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_og_image(page_url):
    try:
        page_html = fetch_text(page_url, timeout=15)
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', page_html, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', page_html, re.I)
        if m:
            return urllib.parse.urljoin(page_url, m.group(1))
    except Exception:
        pass
    return ""


def parse_rss(url, veiculo, limit=4, fetch_cover_for_first=True):
    items = []
    try:
        xml_text = fetch_text(url)
        root = ET.fromstring(xml_text)
        for idx, item in enumerate(root.findall(".//item")[:limit]):
            title = clean_html_text(item.findtext("title") or "")
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()[:16]
            desc = clean_html_text(item.findtext("description") or "")[:220]
            if desc and len(desc) == 220:
                desc = desc.rsplit(" ", 1)[0] + "..."
            img = ""
            # Check media:content or enclosure in RSS first
            for child in item:
                tag_low = child.tag.lower()
                if tag_low.endswith("content") or tag_low.endswith("thumbnail") or tag_low == "enclosure":
                    cand = child.attrib.get("url", "")
                    if cand and re.search(r"\.(jpg|jpeg|png|webp)", cand, re.I):
                        img = cand
                        break
            if not img and fetch_cover_for_first and idx == 0 and link:
                img = extract_og_image(link)

            if title and link:
                items.append({
                    "veiculo": veiculo,
                    "titulo": title,
                    "resumo": desc,
                    "url": link,
                    "imagem": img,
                    "data": pub
                })
    except Exception as exc:
        print(f"Aviso ao ler RSS de {veiculo}: {exc}")
    return items


def find_averdade_jav_cover(home_html):
    # Exact pattern used by Jornal A Verdade weekly print cover: .../wp-content/uploads/YYYY/MM/jav344.jpeg
    jav_matches = re.findall(
        r'https?://averdade\.org\.br/wp-content/uploads/[^"\'\s<>]+/jav\d+[^"\'\s<>]*\.(?:jpg|jpeg|png|webp)',
        home_html,
        re.I
    )
    if jav_matches:
        # Strip WordPress resize suffix (-300x400) if present to grab the crisp full-page cover
        best = re.sub(r"-\d+x\d+(?=\.(?:jpg|jpeg|png|webp)$)", "", jav_matches[0], flags=re.I)
        return best

    # Secondary check: relative or protocol-less uploads path with javNNN
    rel_matches = re.findall(
        r'[^"\'\s<>]*wp-content/uploads/[^"\'\s<>]+/jav\d+[^"\'\s<>]*\.(?:jpg|jpeg|png|webp)',
        home_html,
        re.I
    )
    if rel_matches:
        best = re.sub(r"-\d+x\d+(?=\.(?:jpg|jpeg|png|webp)$)", "", rel_matches[0], flags=re.I)
        return urllib.parse.urljoin("https://averdade.org.br/", best)

    return ""


def fetch_averdade():
    local_rel_path = "img/capa-a-verdade.jpg"
    os.makedirs("img", exist_ok=True)
    capa = {
        "titulo": "Jornal A Verdade — Edição Semanal",
        "edicao": "",
        "descricao": "Capa da edição impressa extraída diretamente do arquivo oficial (padrão javNNN) do Jornal A Verdade.",
        "url": "https://averdade.org.br/",
        "imagem": local_rel_path if os.path.exists(local_rel_path) else "",
        "origem_url": ""
    }
    try:
        html = fetch_text("https://averdade.org.br/")
        img_url = find_averdade_jav_cover(html)

        # Extract edition number from jav344 filename or page text
        ed_from_file = re.search(r"jav(\d{2,4})", img_url, re.I)
        ed_from_text = re.search(r"Edi[çc][ãa]o\s*(?:n[º°]?\s*)?(\d{2,4})", html, re.I)
        ed_num = ed_from_file.group(1) if ed_from_file else (ed_from_text.group(1) if ed_from_text else "")
        if ed_num:
            capa["edicao"] = f"Edição nº {ed_num}"
            capa["titulo"] = f"Jornal A Verdade — Edição nº {ed_num}"

        ed_href = re.search(r'href=["\'](https?://averdade\.org\.br/[^"\']*edica[^"\']*)["\']', html, re.I)
        if ed_href:
            capa["url"] = ed_href.group(1)

        if img_url:
            capa["origem_url"] = img_url
            img_bytes = fetch_bytes(img_url)
            if len(img_bytes) > 5000:
                with open(local_rel_path, "wb") as f:
                    f.write(img_bytes)
                capa["imagem"] = local_rel_path
                print(f"Capa exata salva em {local_rel_path} a partir de {img_url} ({len(img_bytes)} bytes).")
    except Exception as exc:
        print(f"Aviso ao baixar capa do A Verdade: {exc}")
    return capa


def main():
    icl_items = parse_rss("https://iclnoticias.com.br/politica/feed/", "ICL Notícias • Política", limit=4, fetch_cover_for_first=True)
    if not icl_items:
        icl_items = parse_rss("https://iclnoticias.com.br/feed/", "ICL Notícias", limit=4, fetch_cover_for_first=True)

    bdf_items = parse_rss("https://www.brasildefato.com.br/feed/", "Brasil de Fato", limit=4, fetch_cover_for_first=True)
    av_items = parse_rss("https://averdade.org.br/feed/", "Jornal A Verdade", limit=2, fetch_cover_for_first=False)

    destaques_ao_vivo = []
    if icl_items:
        destaques_ao_vivo.append(icl_items[0])
    if bdf_items:
        destaques_ao_vivo.append(bdf_items[0])

    manchetes = []
    manchetes.extend(icl_items)
    manchetes.extend(bdf_items)
    manchetes.extend(av_items)

    capa = fetch_averdade()

    if not manchetes and not capa.get("imagem"):
        print("Nenhuma atualização coletada; mantendo arquivos anteriores.")
        return

    os.makedirs("data", exist_ok=True)
    payload = {
        "atualizado_em": datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "capa_averdade": capa,
        "destaques_ao_vivo": destaques_ao_vivo,
        "manchetes": manchetes
    }
    with open("data/noticias.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Atualizado: {len(destaques_ao_vivo)} destaques ao vivo, {len(manchetes)} manchetes, capa={capa.get('origem_url')}.")


if __name__ == "__main__":
    main()
