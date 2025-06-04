# sites_config.py

SITES = {
    "Links": {
        # URL za pretragu; {query} će biti zamijenjen s primjerice "logitech+g+pro+x2"
        "search_url": "https://www.links.hr/hr/search?q={query}",

        # Selektor za svaki <a> koji vodi na proizvod
        "item_selector": "a.card-link",

        # Naziv je u atributu title tog <a>
        "title_attr": "title",
        "title_in_span": False,

        # Selektor unutar iste <a> (ili u blizini) za element s cijenom
        "price_selector": "span.price-new",

        # Prefiks za relativni href
        "url_prefix": "https://www.links.hr",
    },

    "Instar": {
        "search_url": "https://www.instar-informatika.hr/Search/?fs=1&term={query}",

        # Selektor za svaki <a class="productEntityClick">
        "item_selector": "a.productEntityClick",

        # Naziv je unutar <span>…</span> tog <a>
        "title_attr": None,
        "title_in_span": True,

        # Selektor za cijenu
        "price_selector": "div.price",

        # Prefiks za relativni href
        "url_prefix": "https://www.instar-informatika.hr",
    },

    "SkinPort": {
        # Kada tražiš skin, URL je u obliku:
        #   https://skinbaron.de/en/search?searchString=AK%E2% 80% 94Redline
        # Dakle, query je “AK-47+Redline” (URL‐encoded).
        "search_url": "https://skinport.com/market?search={query}",

        # Svaki rezultat na SkinBaron stranici unutar <div class="item-info"> 
        # (ovo je ilustrativno – otvori DevTools i pronađi pravi selektor)
        "item_selector": "a.ItemPreview-link",

        # U okviru tog <div class="item-info"> naziv skina dolazi npr. u 
        # <a class="item-title" title="AK-47 | Redline">AK-47 | Redline</a>
        "title_attr": "title",
        "title_in_span": False,

        # Cijena se obično nalazi u <span class="price">11,50 €</span>
        # ili unutar <div class="price">, pa prilagodi nakon što pregledaš
        "price_selector": "div.Tooltip-link",

        # Ako u <a href="/en/item/12345">, prefix je:
        "url_prefix": "https://skinport.com",
    },

    "SkinBaron": {
        # Pretraga na SkinPortu: https://skinport.com/search?q=<query>
        "search_url": "https://skinbaron.de/en/csgo?str={query}&sort=PA",

        # Rezultati su u npr. <a class="item-link"> unutar <div class="item listing">
        "item_selector": ".click-wrapper",

        # U <a class="item-link" title="AK-47 | Redline"> naziv je u title atributu
        "title_attr": "title",
        "title_in_span": False,

        # Cijena u <span class="price">12.30 €</span>
        "price_selector": ".price item",

        "url_prefix": "https://skinbaron.de",
    },

}
