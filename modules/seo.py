from aiocache import cached
from modules.data import get_config, get_seo_page_data




@cached(ttl=3600)
async def default_page(page_name: str, path=None) -> list:
    seo_texts = []
    config_data = await get_config()

    site_domain = config_data.get("domain", "")
    global_tagline = config_data.get("tagline", "")
    site_title = config_data.get("title", "")
    default_description = config_data.get("description", "")
    favicon_url = config_data.get("favicon", "")
    if not favicon_url.startswith("http"):
        favicon_url = f"https://{site_domain}/{favicon_url.lstrip('/')}"

    seo_data = await get_seo_page_data()
    page_data = seo_data.get("pages", {}).get(page_name, {})

    default_keywords = seo_data.get("default_keywords", [])

    page_title = page_data.get("title", f"{site_title} - {global_tagline}")
    page_description = page_data.get("description", default_description)
    keywords = ', '.join(page_data.get("keywords", default_keywords))

    if path is None:
        path = page_name

    seo_texts.append(f"<meta name='description' content='{page_description}' />")
    seo_texts.append(f"<link rel='canonical' href='https://{site_domain}/{path}' />")
    seo_texts.append(f"<meta property='og:url' content='https://{site_domain}/{path}' />")
    seo_texts.append(f"<meta name='twitter:url' content='https://{site_domain}/{path}' />")
    seo_texts.append(f"<meta property='og:site_name' content='{site_title}' />")
    seo_texts.append(f"<meta name='twitter:site' content='@{site_title}' />")
    seo_texts.append(f"<meta name='twitter:card' content='summary_large_image' />")
    seo_texts.append(f"<meta name='twitter:creator' content='@{site_title}' />")
    seo_texts.append(f"<meta property='og:type' content='website' />")
    seo_texts.append(f"<meta property='og:title' content='{page_title}' />")
    seo_texts.append(f"<meta name='twitter:title' content='{page_title}' />")
    seo_texts.append(f"<meta property='og:description' content='{page_description}' />")
    seo_texts.append(f"<meta name='twitter:description' content='{page_description}' />")
    seo_texts.append(f"<meta property='og:image' content='{favicon_url}' />")
    seo_texts.append(f"<meta name='twitter:image' content='{favicon_url}' />")
    seo_texts.append(f"<meta name='keywords' content='{keywords}' />")

    return seo_texts

@cached(ttl=3600)
async def home_page() -> list:
    return await default_page("home", path="")

@cached(ttl=3600)
async def login_page() -> list:
    return await default_page("login", path="login")

@cached(ttl=3600)
async def signup_page() -> list:
    return await default_page("signup", path="signup")

@cached(ttl=3600)
async def services_page() -> list:
    return await default_page("services", path="services")

@cached(ttl=3600)
async def contact_page() -> list:
    return await default_page("contact", path="contact")

@cached(ttl=3600)
async def policy_page() -> list:
    return await default_page("policy", path="policy")

@cached(ttl=3600)
async def about_page() -> list:
    return await default_page("about", path="about")

@cached(ttl=3600)
async def generate_seo_texts(page: str,path=None) -> list:
    try:
        if page == "home":
            return await home_page()
        elif page == "login":
            return await login_page()
        elif page == "signup":
            return await signup_page()
        elif page == "services":
            return await services_page()
        elif page == "contact":
            return await contact_page()
        elif page == "policy":
            return await policy_page()
        elif page == "about":
            return await about_page()
        else:
            return await default_page(page_name=page,path=path if path else page)
    except Exception as e:
        print(f"SEO generation error for page '{page}': {e}")
        return []