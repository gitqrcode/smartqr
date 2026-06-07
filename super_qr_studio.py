# super_qr_studio.py
import os
import math
import json
import base64
import datetime
import urllib.parse
from io import BytesIO
from typing import Optional, List, Dict

import requests
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, CircleModuleDrawer, SquareModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask, HorizontalGradiantColorMask, SolidFillColorMask
from PIL import Image, ImageDraw, ImageSequence, ImageOps

# ==========================================
# PART 1: 30-PAYLOAD QR CODE BUILDER ENGINE
# ==========================================
class QRPayloadBuilder:
    @staticmethod
    def build(qr_type: str, data: dict) -> str:
        """Dispatches data formatting according to the selected QR type."""
        try:
            method = getattr(QRPayloadBuilder, f"_build_{qr_type.lower()}", None)
            if method:
                return method(data)
            return data.get("text", "")
        except Exception as e:
            return f"Error building payload: {str(e)}"

    @staticmethod
    def _build_text(d: dict) -> str: return d.get("text", "")
    @staticmethod
    def _build_url(d: dict) -> str:
        url = d.get("url", "")
        return url if url.startswith(("http://", "https://")) else "https://" + url
    @staticmethod
    def _build_email(d: dict) -> str:
        return f"mailto:{d.get('email', '')}?subject={urllib.parse.quote(d.get('subject', ''))}&body={urllib.parse.quote(d.get('body', ''))}"
    @staticmethod
    def _build_phone(d: dict) -> str: return f"tel:{d.get('phone', '')}"
    @staticmethod
    def _build_sms(d: dict) -> str: return f"sms:{d.get('phone', '')}?body={urllib.parse.quote(d.get('message', ''))}"
    @staticmethod
    def _build_whatsapp(d: dict) -> str: return f"https://wa.me/{d.get('phone', '')}?text={urllib.parse.quote(d.get('message', ''))}"
    @staticmethod
    def _build_telegram(d: dict) -> str: return f"https://t.me/{d.get('username', '')}"
    @staticmethod
    def _build_skype(d: dict) -> str: return f"skype:{d.get('username', '')}?{d.get('action', 'chat')}"
    @staticmethod
    def _build_discord(d: dict) -> str: return f"https://discord.gg/{d.get('invite_code', '')}"
    @staticmethod
    def _build_wifi(d: dict) -> str:
        hid = "true" if d.get("hidden") else "false"
        return f"WIFI:S:{d.get('ssid','')};T:{d.get('encryption','WPA')};P:{d.get('password','')};H:{hid};;"
    @staticmethod
    def _build_vcard(d: dict) -> str:
        return f"BEGIN:VCARD\nVERSION:3.0\nN:{d.get('last_name','')};{d.get('first_name','')};;;\nFN:{d.get('first_name','')} {d.get('last_name','')}\nORG:{d.get('org','')}\nTITLE:{d.get('title','')}\nTEL;TYPE=WORK,VOICE:{d.get('phone','')}\nEMAIL;TYPE=PREF,INTERNET:{d.get('email','')}\nURL:{d.get('url','')}\nEND:VCARD"
    @staticmethod
    def _build_mecard(d: dict) -> str:
        return f"MECARD:N:{d.get('last_name','')},{d.get('first_name','')};TEL:{d.get('phone','')};EMAIL:{d.get('email','')};;"
    @staticmethod
    def _build_calendar(d: dict) -> str:
        return f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:{d.get('summary','')}\nDTSTART:{d.get('dtstart','')}\nDTEND:{d.get('dtend','')}\nDESCRIPTION:{d.get('description','')}\nLOCATION:{d.get('location','')}\nEND:VEVENT\nEND:VCALENDAR"
    @staticmethod
    def _build_gps(d: dict) -> str: return f"geo:{d.get('lat', '0')},{d.get('lon', '0')}"
    @staticmethod
    def _build_gmaps(d: dict) -> str: return f"https://www.google.com/maps/dir/?api=1&destination={d.get('lat', '0')},{d.get('lon', '0')}"
    @staticmethod
    def _build_instagram(d: dict) -> str: return f"https://instagram.com/{d.get('username', '')}"
    @staticmethod
    def _build_twitter(d: dict) -> str: return f"https://x.com/{d.get('username', '')}"
    @staticmethod
    def _build_tweet(d: dict) -> str: return f"https://twitter.com/intent/tweet?text={urllib.parse.quote(d.get('text', ''))}"
    @staticmethod
    def _build_linkedin(d: dict) -> str: return d.get("url", "")
    @staticmethod
    def _build_youtube(d: dict) -> str: return f"https://youtube.com/{d.get('channel_or_video', '')}"
    @staticmethod
    def _build_tiktok(d: dict) -> str: return f"https://www.tiktok.com/@{d.get('username', '')}"
    @staticmethod
    def _build_facebook(d: dict) -> str: return f"https://facebook.com/{d.get('profile', '')}"
    @staticmethod
    def _build_paypal(d: dict) -> str:
        return f"https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business={d.get('merchant', '')}&item_name={urllib.parse.quote(d.get('item', ''))}&amount={d.get('amount', 0)}&currency_code={d.get('currency', 'USD')}"
    @staticmethod
    def _build_shopify(d: dict) -> str: return f"https://{d.get('store', '')}.myshopify.com/cart/{d.get('variant', '')}:{d.get('qty', 1)}"
    @staticmethod
    def _build_bitcoin(d: dict) -> str:
        base = f"bitcoin:{d.get('address', '')}"
        p = []
        if d.get("amount"): p.append(f"amount={d.get('amount')}")
        if d.get("label"): p.append(f"label={urllib.parse.quote(d.get('label'))}")
        return f"{base}?{'&'.join(p)}" if p else base
    @staticmethod
    def _build_ethereum(d: dict) -> str:
        base = f"ethereum:{d.get('address', '')}"
        return f"{base}?value={d.get('value', '')}" if d.get('value') else base
    @staticmethod
    def _build_deeplink(d: dict) -> str: return f"{d.get('scheme', '')}://{d.get('path', '')}"
    @staticmethod
    def _build_zoom(d: dict) -> str:
        pwd = f"&pwd={d.get('password', '')}" if d.get('password') else ""
        return f"zoommtg://zoom.us/join?confno={d.get('meeting_id', '')}{pwd}"
    @staticmethod
    def _build_hosted_file(d: dict) -> str: return d.get("url", "")
    @staticmethod
    def _build_dynamic(d: dict) -> str:
        return f"{d.get('endpoint', '')}/{d.get('qr_id', '')}?utm_source={d.get('utm_source', 'qr_code')}"


# ==========================================
# PART 2: VISUAL STYLING & MEDIA GENERATION
# ==========================================
class CustomQREngine:
    @staticmethod
    def generate_static(
        payload: str,
        style: str = "rounded",
        color_type: str = "solid",
        front_color: tuple = (0, 0, 0),
        back_color: tuple = (255, 255, 255),
        gradient_color: tuple = (0, 0, 255),
        logo_bytes: bytes = None,
        custom_eyes: bool = True
    ) -> bytes:
        drawer_map = {
            "rounded": RoundedModuleDrawer(),
            "circle": CircleModuleDrawer(),
            "square": SquareModuleDrawer()
        }
        drawer = drawer_map.get(style, RoundedModuleDrawer())

        if color_type == "radial_gradient":
            mask = RadialGradiantColorMask(back_color=back_color, edge_color=gradient_color, center_color=front_color)
        elif color_type == "linear_gradient":
            mask = HorizontalGradiantColorMask(back_color=back_color, left_color=front_color, right_color=gradient_color)
        else:
            mask = SolidFillColorMask(back_color=back_color, front_color=front_color)

        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
        qr.add_data(payload)
        qr.make(fit=True)

        qr_img = qr.make_image(image_factory=StyledPilImage, module_drawer=drawer, color_mask=mask).convert("RGBA")

        if custom_eyes:
            qr_img = CustomQREngine._apply_custom_eyes(qr_img, qr.version, 4, front_color, back_color)

        if logo_bytes:
            logo = Image.open(BytesIO(logo_bytes)).convert("RGBA")
            qr_w, qr_h = qr_img.size
            logo_size = int(qr_w * 0.20)
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            
            pad = Image.new("RGBA", (logo_size + 12, logo_size + 12), back_color)
            qr_img.paste(pad, ((qr_w - logo_size - 12) // 2, (qr_h - logo_size - 12) // 2), pad)
            qr_img.paste(logo, ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2), logo)

        out_buffer = BytesIO()
        qr_img.save(out_buffer, format="PNG")
        return out_buffer.getvalue()

    @staticmethod
    def _apply_custom_eyes(img: Image.Image, version: int, border: int, front: tuple, back: tuple) -> Image.Image:
        draw = ImageDraw.Draw(img)
        side_modules = (17 + version * 4) + (border * 2)
        box_size = 10
        total_px = side_modules * box_size
        eye_px = 7 * box_size
        quiet_px = border * box_size

        positions = [
            (quiet_px, quiet_px),
            (total_px - quiet_px - eye_px, quiet_px),
            (quiet_px, total_px - quiet_px - eye_px)
        ]

        for x, y in positions:
            draw.rounded_rectangle([x, y, x + eye_px - 1, y + eye_px - 1], radius=18, fill=front)
            draw.rounded_rectangle([x + box_size, y + box_size, x + eye_px - box_size - 1, y + eye_px - box_size - 1], radius=12, fill=back)
            draw.rounded_rectangle([x + 2*box_size, y + 2*box_size, x + eye_px - 2*box_size - 1, y + eye_px - 2*box_size - 1], radius=8, fill=front)

        return img

    @staticmethod
    def generate_animated(payload: str, gif_bytes: bytes, logo_bytes: Optional[bytes] = None) -> bytes:
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
        qr.add_data(payload)
        qr.make(fit=True)
        
        qr_raw = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
        qr_w, qr_h = qr_raw.size

        pixels = qr_raw.getdata()
        transparent_pixels = []
        for p in pixels:
            if p[0] > 200 and p[1] > 200 and p[2] > 200:
                transparent_pixels.append((255, 255, 255, 0))
            else:
                transparent_pixels.append((0, 0, 0, 255))
        qr_raw.putdata(transparent_pixels)

        bg_gif = Image.open(BytesIO(gif_bytes))
        bg_frames = [f.copy().convert("RGBA").resize((qr_w, qr_h), Image.Resampling.LANCZOS) for f in ImageSequence.Iterator(bg_gif)]

        logo_frames = []
        if logo_bytes:
            try:
                logo_gif = Image.open(BytesIO(logo_bytes))
                logo_size = int(qr_w * 0.20)
                logo_frames = [f.copy().convert("RGBA").resize((logo_size, logo_size), Image.Resampling.LANCZOS) for f in ImageSequence.Iterator(logo_gif)]
            except:
                static_logo = Image.open(BytesIO(logo_bytes)).convert("RGBA")
                logo_size = int(qr_w * 0.20)
                static_logo = static_logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                logo_frames = [static_logo]

        composite_frames = []
        logo_size = int(qr_w * 0.20) if logo_bytes else 0

        for i, bg_frame in enumerate(bg_frames):
            contrast_bg = Image.blend(bg_frame, Image.new("RGBA", (qr_w, qr_h), (255, 255, 255, 255)), 0.6)
            composite = Image.alpha_composite(contrast_bg, qr_raw)
            
            if logo_frames:
                current_logo_frame = logo_frames[i % len(logo_frames)]
                pad = Image.new("RGBA", (logo_size + 12, logo_size + 12), (255, 255, 255, 255))
                composite.paste(pad, ((qr_w - logo_size - 12) // 2, (qr_h - logo_size - 12) // 2), pad)
                composite.paste(current_logo_frame, ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2), current_logo_frame)
            
            composite_frames.append(composite)

        out_buffer = BytesIO()
        composite_frames[0].save(
            out_buffer,
            format="GIF",
            save_all=True,
            append_images=composite_frames[1:],
            loop=0,
            duration=bg_gif.info.get("duration", 100),
            disposal=2
        )
        return out_buffer.getvalue()


# ==========================================
# PART 3: REDIRECTION, CAMPAIGNS, AND SERVER
# ==========================================
app = FastAPI(title="Super QR Studio Engine")

def sanitize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

DB_CAMPAIGNS = {
    "promo_2026": {
        "primary_url": "https://instabase.com",
        "fallback_url": "https://instabase.com/404",
        "launch_date": "2026-06-01T09:00",
        "expiry_date": "2026-12-31T23:59",
        "max_scans": 1000,
        "scans_count": 0,
        "password": "",
        "meta_pixel_id": "",
        "google_analytics_id": "",
        "os_redirection": {
            "iOS": "https://apps.apple.com/us/app/example",
            "Android": "https://play.google.com/store/apps"
        },
        "geo_redirection": {
            "FR": "https://fr.instabase.com"
        },
        "geofence": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "radius_meters": 1000,
            "blocked_redirect": "https://instabase.com/restricted-location"
        }
    }
}
DB_ANALYTICS = []

def parse_os(ua: str) -> str:
    ua = ua.lower()
    if "iphone" in ua or "ipad" in ua: return "iOS"
    if "android" in ua: return "Android"
    return "Desktop"

def get_country_ip(ip: str) -> str:
    try:
        res = requests.get(f"https://ipapi.co/{ip}/json/", timeout=1.0).json()
        return res.get("country_code", "US")
    except:
        return "US"

@app.get("/api/campaigns")
def list_campaigns():
    return DB_CAMPAIGNS

@app.get("/api/analytics")
def list_analytics():
    return DB_ANALYTICS

@app.post("/r/{qr_id}/auth", response_class=HTMLResponse)
def handle_password_auth(qr_id: str, request: Request, password_attempt: str = Form(...)):
    if qr_id not in DB_CAMPAIGNS:
        raise HTTPException(status_code=404)
    
    cfg = DB_CAMPAIGNS[qr_id]
    if password_attempt == cfg.get("password", ""):
        return redirect_gateway_flow(qr_id, request)
    
    return serve_password_gate(qr_id, error="Invalid password. Access Denied.")

@app.get("/r/{qr_id}", response_class=HTMLResponse)
def redirect_gateway(qr_id: str, request: Request):
    if qr_id not in DB_CAMPAIGNS:
        raise HTTPException(status_code=404, detail="Campaign profile not found.")

    cfg = DB_CAMPAIGNS[qr_id]
    
    if cfg.get("password"):
        return serve_password_gate(qr_id)

    return redirect_gateway_flow(qr_id, request)

def serve_password_gate(qr_id: str, error: str = "") -> str:
    err_block = f"<div class='bg-red-950/40 border border-red-800 text-red-400 p-3 rounded-lg text-sm mb-4 font-semibold'>{error}</div>" if error else ""
    return f"""
    <html>
    <head>
        <title>Secure Destination Access</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 flex items-center justify-center min-h-screen">
        <div class="max-w-md w-full bg-slate-950 p-8 rounded-xl border border-slate-800 shadow-xl text-center">
            <h1 class="text-2xl font-bold mb-2">Password Protected</h1>
            <p class="text-sm text-slate-400 mb-6">You must enter the authorization passcode to access this destination.</p>
            {err_block}
            <form action="/r/{qr_id}/auth" method="POST" class="space-y-4">
                <input type="password" name="password_attempt" required placeholder="Enter Passcode" class="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-slate-100 text-center focus:ring-2 focus:ring-indigo-500 outline-none">
                <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-500 py-3 rounded-lg font-bold transition-all">Submit Access Key</button>
            </form>
        </div>
    </body>
    </html>
    """

def redirect_gateway_flow(qr_id: str, request: Request):
    cfg = DB_CAMPAIGNS[qr_id]
    now = datetime.datetime.now()

    if cfg.get("launch_date"):
        try:
            ld = datetime.datetime.fromisoformat(cfg["launch_date"])
            if now < ld:
                return f"""
                <html>
                <body style="font-family:sans-serif; text-align:center; padding:100px; background:#F8FAFC;">
                    <div style="max-width:500px; margin:0 auto; background:white; padding:40px; border-radius:12px; box-shadow:0 4px 6px -1px rgba(0,0,0,0.1);">
                        <h1 style="color:#1E293B; margin-bottom:12px;">Campaign Inactive</h1>
                        <p style="color:#64748B;">This exclusive promotional window goes live on {ld.strftime('%B %d, %Y at %I:%M %p')}.</p>
                    </div>
                </body>
                </html>
                """
        except: pass

    if cfg.get("expiry_date"):
        try:
            ed = datetime.datetime.fromisoformat(cfg["expiry_date"])
            if now > ed:
                return RedirectResponse(url=cfg["fallback_url"])
        except: pass

    if cfg.get("max_scans") and cfg["scans_count"] >= cfg["max_scans"]:
        return RedirectResponse(url=cfg["fallback_url"])

    cfg["scans_count"] += 1
    ua = request.headers.get("user-agent", "")
    client_ip = request.client.host

    if cfg.get("geofence") and cfg["geofence"].get("latitude"):
        return f"""
        <html>
        <head>
            <script>
                window.onload = function() {{
                    if (navigator.geolocation) {{
                        navigator.geolocation.getCurrentPosition(
                            function(p) {{
                                document.getElementById("lat").value = p.coords.latitude;
                                document.getElementById("lon").value = p.coords.longitude;
                                document.getElementById("geoForm").submit();
                            }},
                            function() {{
                                alert("This campaign requires location access to confirm your location.");
                                window.location.href = "{cfg['fallback_url']}";
                            }}
                        );
                    }} else {{
                        window.location.href = "{cfg['fallback_url']}";
                    }}
                }}
            </script>
        </head>
        <body style="font-family:sans-serif; text-align:center; padding-top:100px;">
            <p>Authenticating location...</p>
            <form id="geoForm" action="/verify_gps/{qr_id}" method="POST">
                <input type="hidden" name="latitude" id="lat">
                <input type="hidden" name="longitude" id="lon">
            </form>
        </body>
        </html>
        """

    target = cfg["primary_url"]
    os_type = parse_os(ua)
    if cfg.get("os_redirection") and cfg["os_redirection"].get(os_type):
        target = cfg["os_redirection"][os_type]
    else:
        country = get_country_ip(client_ip)
        if cfg.get("geo_redirection") and cfg["geo_redirection"].get(country):
            target = cfg["geo_redirection"][country]

    DB_ANALYTICS.append({
        "qr_id": qr_id,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "ip": client_ip,
        "device": os_type,
        "country": get_country_ip(client_ip)
    })

    px_m = f"<script>!function(f,b,e,v,n,t,s){{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)}};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');fbq('init', '{cfg['meta_pixel_id']}');fbq('track', 'PageView');</script>" if cfg.get("meta_pixel_id") else ""
    px_g = f"<script async src='https://www.googletagmanager.com/gtag/js?id={cfg['google_analytics_id']}'></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{cfg['google_analytics_id']}');</script>" if cfg.get("google_analytics_id") else ""

    return f"""
    <html>
    <head>
        {px_m}
        {px_g}
        <script>
            setTimeout(function() {{ window.location.href = "{target}"; }}, 250);
        </script>
    </head>
    <body style="font-family:sans-serif; text-align:center; padding-top:150px; background:#F8FAFC;">
        <p style="color:#64748B;">Routing to secure destination...</p>
    </body>
    </html>
    """

@app.post("/verify_gps/{qr_id}")
def verify_gps(qr_id: str, latitude: float = Form(...), longitude: float = Form(...)):
    if qr_id not in DB_CAMPAIGNS: raise HTTPException(status_code=404)
    cfg = DB_CAMPAIGNS[qr_id]
    gf = cfg["geofence"]

    lat1, lon1 = math.radians(latitude), math.radians(longitude)
    lat2, lon2 = math.radians(gf["latitude"]), math.radians(gf["longitude"])
    
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    dist = 6371000 * c

    if dist <= gf["radius_meters"]:
        return RedirectResponse(url=cfg["primary_url"], status_code=303)
    return RedirectResponse(url=gf["blocked_redirect"], status_code=303)


# ==========================================
# PART 4: FRONTEND DASHBOARD INTERFACE UI
# ==========================================
@app.post("/api/generate")
async def api_generate(
    request: Request, # Access request properties to read client hostname dynamically
    qr_type: str = Form(...),
    payload_data: str = Form(...),
    style: str = Form("rounded"),
    color_type: str = Form("solid"),
    front_color: str = Form("#000000"),
    back_color: str = Form("#ffffff"),
    gradient_color: str = Form("#0000ff"),
    custom_eyes: bool = Form(True),
    logo: UploadFile = File(None),
    bg_gif: UploadFile = File(None),
    is_dynamic: bool = Form(False),
    qr_id: str = Form(None),
    # Campaign Rules
    primary_url: str = Form(""),
    fallback_url: str = Form(""),
    launch_date: str = Form(""),
    expiry_date: str = Form(""),
    max_scans: int = Form(1000),
    password: str = Form(""),
    meta_pixel_id: str = Form(""),
    google_analytics_id: str = Form(""),
    ios_url: str = Form(""),
    android_url: str = Form(""),
    fr_url: str = Form(""),
    geofence_lat: float = Form(None),
    geofence_lon: float = Form(None),
    geofence_rad: float = Form(1000),
    geofence_blocked: str = Form("")
):
    try:
        p_data = json.loads(payload_data)
        
        if is_dynamic and qr_id:
            # SANITIZATION: Force absolute URLs to prevent internal folder routing bugs
            sanitized_primary = sanitize_url(primary_url or p_data.get("url", "https://instabase.com"))
            sanitized_fallback = sanitize_url(fallback_url or "https://instabase.com/404")
            sanitized_ios = sanitize_url(ios_url)
            sanitized_android = sanitize_url(android_url)
            sanitized_fr = sanitize_url(fr_url)
            sanitized_geo_blocked = sanitize_url(geofence_blocked)

            DB_CAMPAIGNS[qr_id] = {
                "primary_url": sanitized_primary,
                "fallback_url": sanitized_fallback,
                "launch_date": launch_date,
                "expiry_date": expiry_date,
                "max_scans": max_scans,
                "scans_count": 0,
                "password": password,
                "meta_pixel_id": meta_pixel_id,
                "google_analytics_id": google_analytics_id,
                "os_redirection": {
                    "iOS": sanitized_ios,
                    "Android": sanitized_android
                },
                "geo_redirection": {
                    "FR": sanitized_fr
                },
                "geofence": {
                    "latitude": geofence_lat,
                    "longitude": geofence_lon,
                    "radius_meters": geofence_rad,
                    "blocked_redirect": sanitized_geo_blocked
                }
            }
            # Dynamically determine host path (e.g. http://192.168.1.15:8000)
            base_server_host = str(request.base_url).rstrip('/')
            payload = QRPayloadBuilder.build("dynamic", {
                "endpoint": f"{base_server_host}/r",
                "qr_id": qr_id
            })
        else:
            payload = QRPayloadBuilder.build(qr_type, p_data)

        def hex_to_rgb(hex_str):
            hex_str = hex_str.lstrip('#')
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

        fc = hex_to_rgb(front_color)
        bc = hex_to_rgb(back_color)
        gc = hex_to_rgb(gradient_color)

        logo_bytes = await logo.read() if logo else None
        gif_bytes = await bg_gif.read() if bg_gif else None

        if gif_bytes:
            img_bytes = CustomQREngine.generate_animated(payload, gif_bytes, logo_bytes)
            mime_type = "image/gif"
        else:
            img_bytes = CustomQREngine.generate_static(
                payload, style, color_type, fc, bc, gc, logo_bytes, custom_eyes
            )
            mime_type = "image/png"

        b64_str = base64.b64encode(img_bytes).decode("utf-8")
        return JSONResponse({
            "status": "success",
            "image": f"data:{mime_type};base64,{b64_str}",
            "payload": payload,
            "qr_id": qr_id if is_dynamic else None
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)


@app.get("/", response_class=HTMLResponse)
def index_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Super QR Studio Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-slate-900 text-slate-100 min-h-screen">
        <header class="border-b border-slate-800 bg-slate-950 py-4 px-6 flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <i class="fa-solid fa-qrcode text-indigo-500 text-3xl"></i>
                <h1 class="text-xl font-bold tracking-tight">Super QR Studio</h1>
            </div>
            <div class="text-sm text-slate-400">Status: <span class="text-emerald-500 font-semibold">● Active API Engine</span></div>
        </header>

        <main class="max-w-7xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
            <!-- Left Side Inputs -->
            <form id="qrForm" class="lg:col-span-8 space-y-6" onsubmit="event.preventDefault(); generateQR();">
                <!-- Tab Section 1: Payload Type -->
                <div class="bg-slate-950 p-6 rounded-xl border border-slate-800">
                    <h2 class="text-lg font-semibold mb-4 text-slate-200"><i class="fa-solid fa-list mr-2 text-indigo-500"></i>1. Select QR Payload Type</h2>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <select id="qr_type" name="qr_type" class="col-span-4 bg-slate-900 border border-slate-800 rounded-lg p-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" onchange="togglePayloadFields()">
                            <option value="url">🌐 Web URL</option>
                            <option value="text">✍️ Plain Text</option>
                            <option value="email">📧 Email Template</option>
                            <option value="phone">📞 Phone Dialer</option>
                            <option value="sms">💬 SMS Message</option>
                            <option value="whatsapp">💬 WhatsApp Message</option>
                            <option value="wifi">📶 Wi-Fi Access Code</option>
                            <option value="vcard">📇 Business vCard v3.0</option>
                            <option value="gps">📍 Raw Coordinates (GPS)</option>
                            <option value="instagram">📸 Instagram Profile</option>
                            <option value="paypal">💳 PayPal Express Payment</option>
                            <option value="zoom">📹 Zoom Meeting Room</option>
                        </select>
                    </div>

                    <!-- Dynamic Payload Specific Input Forms -->
                    <div id="payload_inputs" class="mt-4 p-4 bg-slate-900 rounded-lg border border-slate-800">
                        <div id="fields_url" class="payload-field">
                            <label class="block text-sm text-slate-400 mb-2">Webpage URL</label>
                            <input type="text" id="url_val" value="https://instabase.com" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                        </div>
                    </div>
                </div>

                <!-- Tab Section 2: Visual Designer -->
                <div class="bg-slate-950 p-6 rounded-xl border border-slate-800">
                    <h2 class="text-lg font-semibold mb-4 text-slate-200"><i class="fa-solid fa-palette mr-2 text-indigo-500"></i>2. Custom Visual Styling</h2>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label class="block text-sm text-slate-400 mb-2">Pixel Style</label>
                            <select name="style" class="w-full bg-slate-900 border border-slate-800 rounded p-2 text-slate-100">
                                <option value="rounded">Rounded modules</option>
                                <option value="circle">Circular modules</option>
                                <option value="square">Standard Square</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm text-slate-400 mb-2">Color Mode</label>
                            <select name="color_type" id="color_type" class="w-full bg-slate-900 border border-slate-800 rounded p-2 text-slate-100" onchange="toggleGradients()">
                                <option value="solid">Solid Palette</option>
                                <option value="linear_gradient">Linear Gradient</option>
                                <option value="radial_gradient">Radial Gradient</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm text-slate-400 mb-2">Corner Eyes (Finder Design)</label>
                            <select name="custom_eyes" class="w-full bg-slate-900 border border-slate-800 rounded p-2 text-slate-100">
                                <option value="true">Sleek Custom Circles</option>
                                <option value="false">Standard Corners</option>
                            </select>
                        </div>
                    </div>

                    <div class="grid grid-cols-3 gap-4 mt-4">
                        <div>
                            <label class="block text-sm text-slate-400 mb-2">Front Color</label>
                            <input type="color" name="front_color" value="#6366f1" class="w-full h-10 bg-slate-900 border border-slate-800 rounded">
                        </div>
                        <div id="grad_color_wrapper" class="hidden">
                            <label class="block text-sm text-slate-400 mb-2">Gradient Accent</label>
                            <input type="color" name="gradient_color" value="#ec4899" class="w-full h-10 bg-slate-900 border border-slate-800 rounded">
                        </div>
                        <div>
                            <label class="block text-sm text-slate-400 mb-2">Canvas BG</label>
                            <input type="color" name="back_color" value="#ffffff" class="w-full h-10 bg-slate-900 border border-slate-800 rounded">
                        </div>
                    </div>

                    <!-- Media Assets File Uploads -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6 pt-4 border-t border-slate-800">
                        <div>
                            <label class="block text-sm text-indigo-400 mb-1 flex items-center justify-between">
                                <span>Center Logo Upload</span>
                                <span class="text-xs text-indigo-300">Accepts Animated GIFs & PNGs</span>
                            </label>
                            <input type="file" name="logo" accept="image/*" class="w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-900 file:text-indigo-100 hover:file:bg-indigo-800">
                        </div>
                        <div>
                            <label class="block text-sm text-indigo-400 mb-1 flex items-center justify-between">
                                <span>Animated Background GIF Overlay</span>
                                <span class="text-xs text-pink-300">Accepts .gif only</span>
                            </label>
                            <input type="file" name="bg_gif" accept="image/gif" class="w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-pink-900 file:text-pink-100 hover:file:bg-pink-800">
                        </div>
                    </div>
                </div>

                <!-- Tab Section 3: Dynamic Logic Campaign Controls -->
                <div class="bg-slate-950 p-6 rounded-xl border border-slate-800">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-lg font-semibold text-slate-200"><i class="fa-solid fa-server mr-2 text-indigo-500"></i>3. Dynamic Campaign Rules</h2>
                        <label class="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" id="is_dynamic" name="is_dynamic" value="true" class="sr-only peer" onchange="toggleDynamicPanel()">
                            <div class="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-300 after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                            <span class="ml-3 text-sm font-medium text-slate-300">Enable Dynamic Redirects</span>
                        </label>
                    </div>

                    <div id="dynamic_panel" class="hidden space-y-4 p-4 bg-slate-900 rounded-lg border border-indigo-950">
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <label class="block text-sm text-slate-400 mb-2">Campaign ID</label>
                                <input type="text" name="qr_id" value="black_friday" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                            <div>
                                <label class="block text-sm text-slate-400 mb-2">Max Scans Cap</label>
                                <input type="number" name="max_scans" value="5000" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                            <div>
                                <label class="block text-sm text-amber-400 mb-2"><i class="fa-solid fa-lock mr-1"></i>Password Protection</label>
                                <input type="password" name="password" placeholder="Passcode (Optional)" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm text-slate-400 mb-2">Launch Date</label>
                                <input type="datetime-local" name="launch_date" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                            <div>
                                <label class="block text-sm text-slate-400 mb-2">Expiry Date</label>
                                <input type="datetime-local" name="expiry_date" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-800">
                            <div>
                                <label class="block text-sm text-slate-400 mb-2">iOS App Link Routing</label>
                                <input type="text" name="ios_url" placeholder="https://apps.apple.com/app" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                            <div>
                                <label class="block text-sm text-slate-400 mb-2">Android App Link Routing</label>
                                <input type="text" name="android_url" placeholder="https://play.google.com" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-800">
                            <div>
                                <label class="block text-sm text-slate-400 mb-2">French (FR) Geo Link Routing</label>
                                <input type="text" name="fr_url" placeholder="https://fr.yourdomain.com" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                            <div>
                                <label class="block text-sm text-slate-400 mb-2">Fallback Redirect URL (Expired/Capped)</label>
                                <input type="text" name="fallback_url" value="https://instabase.com" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                        </div>

                        <!-- Geofencing & Pixel parameters -->
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-slate-800">
                            <div>
                                <label class="block text-sm text-slate-400 mb-2">Geofence Latitude</label>
                                <input type="text" name="geofence_lat" placeholder="37.7749" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                            <div>
                                <label class="block text-sm text-slate-400 mb-2">Geofence Longitude</label>
                                <input type="text" name="geofence_lon" placeholder="-122.4194" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                            <div>
                                <label class="block text-sm text-slate-400 mb-2">Fence Radius (meters)</label>
                                <input type="number" name="geofence_rad" value="1000" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                            <div class="col-span-3">
                                <label class="block text-sm text-slate-400 mb-2">Geofence Blocked/Restricted Redirect Link</label>
                                <input type="text" name="geofence_blocked" placeholder="https://instabase.com/restricted" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-800">
                            <div>
                                <label class="block text-sm text-pink-400 mb-2"><i class="fa-brands fa-facebook mr-1"></i>Meta Retargeting Pixel ID</label>
                                <input type="text" name="meta_pixel_id" placeholder="e.g. 123456789" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                            <div>
                                <label class="block text-sm text-emerald-400 mb-2"><i class="fa-brands fa-google mr-1"></i>Google Tag Manager Analytics ID</label>
                                <input type="text" name="google_analytics_id" placeholder="e.g. G-XXXXXXX" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">
                            </div>
                        </div>
                    </div>
                </div>

                <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-4 rounded-xl shadow-lg shadow-indigo-900/30 transition-all text-lg">
                    Generate Studio Assets
                </button>
            </form>

            <!-- Right Column - Real-time Preview Engine & Analytics -->
            <div class="lg:col-span-4 space-y-6">
                <!-- Preview Canvas Box -->
                <div class="bg-slate-950 p-6 rounded-xl border border-slate-800 text-center sticky top-6">
                    <h2 class="text-md font-bold mb-4 tracking-wider uppercase text-slate-300">Live Workspace Preview</h2>
                    <div class="bg-slate-900 border border-slate-800 rounded-lg p-6 flex items-center justify-center min-h-[300px]">
                        <div id="no-preview" class="text-slate-500">
                            <i class="fa-solid fa-qrcode text-6xl mb-3 block text-slate-700"></i>
                            Configure inputs and click Generate to preview.
                        </div>
                        <img id="qr_preview" class="hidden max-w-full rounded shadow" alt="QR Preview">
                    </div>
                    <div id="workspace_actions" class="hidden mt-4 space-y-3">
                        <p class="text-xs text-slate-400 text-left truncate"><span class="font-bold text-slate-200">Raw payload:</span> <span id="qr_payload_desc"></span></p>
                        <p id="dynamic_link_desc" class="text-xs text-indigo-400 text-left hidden font-medium"></p>
                        <button onclick="downloadQR()" class="w-full bg-indigo-600/30 hover:bg-indigo-600 text-indigo-200 hover:text-white border border-indigo-700/50 py-2 rounded font-semibold transition-all text-sm">
                            <i class="fa-solid fa-download mr-1"></i> Download File
                        </button>
                    </div>
                </div>

                <!-- Live Logs Analytics Panel -->
                <div class="bg-slate-950 p-6 rounded-xl border border-slate-800">
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-md font-bold tracking-wider uppercase text-slate-300">Scans Analytics</h2>
                        <button onclick="refreshLogs()" class="text-xs text-slate-400 hover:text-indigo-400"><i class="fa-solid fa-rotate-right mr-1"></i>Refresh</button>
                    </div>
                    <div class="space-y-3 max-h-[350px] overflow-y-auto pr-2" id="analytics_box">
                        <p class="text-xs text-slate-500 text-center py-4">No logged scans captured yet.</p>
                    </div>
                </div>
            </div>
        </main>

        <script>
            function toggleGradients() {
                const type = document.getElementById("color_type").value;
                const wrapper = document.getElementById("grad_color_wrapper");
                if (type.includes("gradient")) {
                    wrapper.classList.remove("hidden");
                } else {
                    wrapper.classList.add("hidden");
                }
            }

            function toggleDynamicPanel() {
                const isChecked = document.getElementById("is_dynamic").checked;
                const panel = document.getElementById("dynamic_panel");
                if (isChecked) {
                    panel.classList.remove("hidden");
                } else {
                    panel.classList.add("hidden");
                }
            }

            const payloadStructures = {
                url: `<label class="block text-sm text-slate-400 mb-2">Webpage URL</label><input type="text" id="url_val" value="https://instabase.com" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">`,
                text: `<label class="block text-sm text-slate-400 mb-2">Plain Text Content</label><textarea id="text_val" rows="3" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">This is text written in the Super QR Studio.</textarea>`,
                email: `<label class="block text-sm text-slate-400 mb-1">To Email Address</label><input type="email" id="email_val" value="test@domain.com" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100 mb-2"><label class="block text-sm text-slate-400 mb-1">Subject</label><input type="text" id="email_subject" value="Inquiry" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100 mb-2"><label class="block text-sm text-slate-400 mb-1">Message Body</label><textarea id="email_body" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"></textarea>`,
                phone: `<label class="block text-sm text-slate-400 mb-2">Phone Number</label><input type="text" id="phone_val" value="+15550199" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">`,
                sms: `<label class="block text-sm text-slate-400 mb-1">Phone Number</label><input type="text" id="sms_phone" value="+15550199" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100 mb-2"><label class="block text-sm text-slate-400 mb-1">SMS Text</label><textarea id="sms_msg" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">Hello!</textarea>`,
                whatsapp: `<label class="block text-sm text-slate-400 mb-1 flex justify-between"><span>WhatsApp Phone Key</span><span class="text-xs text-indigo-300">Format: 15551234 (no +)</span></label><input type="text" id="wa_phone" value="15550199" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100 mb-2"><label class="block text-sm text-slate-400 mb-1">Message Template</label><textarea id="wa_msg" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">Hello!</textarea>`,
                wifi: `<label class="block text-sm text-slate-400 mb-1">Network SSID</label><input type="text" id="wifi_ssid" value="MyHomeWifi" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100 mb-2"><label class="block text-sm text-slate-400 mb-1">SSID Password</label><input type="text" id="wifi_pass" value="password" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100 mb-2"><label class="block text-sm text-slate-400 mb-1">Security Type</label><select id="wifi_enc" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"><option value="WPA">WPA/WPA2</option><option value="WEP">WEP</option><option value="nopass">None</option></select>`,
                vcard: `<div class="grid grid-cols-2 gap-2"><input type="text" id="vc_first" placeholder="First Name" value="John" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"><input type="text" id="vc_last" placeholder="Last Name" value="Doe" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"><input type="text" id="vc_org" placeholder="Organization" value="HQ Inc" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"><input type="text" id="vc_title" placeholder="Title" value="Director" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"><input type="text" id="vc_phone" placeholder="Phone" value="+15551234" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"><input type="email" id="vc_email" placeholder="Email" value="john@hq.com" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"></div>`,
                gps: `<div class="grid grid-cols-2 gap-2"><input type="text" id="gps_lat" placeholder="Latitude" value="37.7749" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"><input type="text" id="gps_lon" placeholder="Longitude" value="-122.4194" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"></div>`,
                instagram: `<label class="block text-sm text-slate-400 mb-2">Instagram Username</label><input type="text" id="ig_username" value="instagram" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">`,
                paypal: `<div class="grid grid-cols-2 gap-2"><input type="text" id="pp_merch" placeholder="PayPal Email/Merchant ID" value="sales@hq.com" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"><input type="text" id="pp_item" placeholder="Product Name" value="Special Promo Ticket" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"><input type="number" id="pp_amt" placeholder="Amount" value="49.99" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"><input type="text" id="pp_curr" placeholder="Currency (USD)" value="USD" class="bg-slate-950 border border-slate-800 rounded p-2 text-slate-100"></div>`,
                zoom: `<label class="block text-sm text-slate-400 mb-1">Meeting ID</label><input type="text" id="zm_id" value="123456789" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100 mb-2"><label class="block text-sm text-slate-400 mb-1">Meeting Passcode</label><input type="text" id="zm_pass" value="98765" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100">`
            };

            function togglePayloadFields() {
                const type = document.getElementById("qr_type").value;
                document.getElementById("payload_inputs").innerHTML = payloadStructures[type] || "No extra fields required.";
            }

            function gatherPayloadData() {
                const type = document.getElementById("qr_type").value;
                if (type === "url") return { url: document.getElementById("url_val").value };
                if (type === "text") return { text: document.getElementById("text_val").value };
                if (type === "email") return { email: document.getElementById("email_val").value, subject: document.getElementById("email_subject").value, body: document.getElementById("email_body").value };
                if (type === "phone") return { phone: document.getElementById("phone_val").value };
                if (type === "sms") return { phone: document.getElementById("sms_phone").value, message: document.getElementById("sms_msg").value };
                if (type === "whatsapp") return { phone: document.getElementById("wa_phone").value, message: document.getElementById("wa_msg").value };
                if (type === "wifi") return { ssid: document.getElementById("wifi_ssid").value, password: document.getElementById("wifi_pass").value, encryption: document.getElementById("wifi_enc").value };
                if (type === "vcard") return { first_name: document.getElementById("vc_first").value, last_name: document.getElementById("vc_last").value, org: document.getElementById("vc_org").value, title: document.getElementById("vc_title").value, phone: document.getElementById("vc_phone").value, email: document.getElementById("vc_email").value };
                if (type === "gps") return { lat: document.getElementById("gps_lat").value, lon: document.getElementById("gps_lon").value };
                if (type === "instagram") return { username: document.getElementById("ig_username").value };
                if (type === "paypal") return { merchant: document.getElementById("pp_merch").value, item: document.getElementById("pp_item").value, amount: document.getElementById("pp_amt").value, currency: document.getElementById("pp_curr").value };
                if (type === "zoom") return { meeting_id: document.getElementById("zm_id").value, password: document.getElementById("zm_pass").value };
                return {};
            }

            async function generateQR() {
                const form = document.getElementById("qrForm");
                const formData = new FormData(form);
                
                const type = document.getElementById("qr_type").value;
                const payloadObj = gatherPayloadData();
                formData.set("payload_data", JSON.stringify(payloadObj));
                formData.set("qr_type", type);

                try {
                    const response = await fetch("/api/generate", {
                        method: "POST",
                        body: formData
                    });
                    const data = await response.json();
                    
                    if (data.status === "success") {
                        document.getElementById("no-preview").classList.add("hidden");
                        const preview = document.getElementById("qr_preview");
                        preview.src = data.image;
                        preview.classList.remove("hidden");
                        
                        document.getElementById("workspace_actions").classList.remove("hidden");
                        document.getElementById("qr_payload_desc").innerText = data.payload;

                        const dyDesc = document.getElementById("dynamic_link_desc");
                        if (data.qr_id) {
                            const baseServerUrl = window.location.origin;
                            dyDesc.innerHTML = `<i class="fa-solid fa-link mr-1"></i> Dynamic Server URL: <a href="${baseServerUrl}/r/${data.qr_id}" target="_blank" class="underline hover:text-indigo-300">${baseServerUrl}/r/${data.qr_id}</a>`;
                            dyDesc.classList.remove("hidden");
                        } else {
                            dyDesc.classList.add("hidden");
                        }
                    } else {
                        alert("Generation error: " + data.message);
                    }
                } catch(err) {
                    alert("Network connection error occurred.");
                }
            }

            function downloadQR() {
                const previewImg = document.getElementById("qr_preview");
                if (!previewImg.src) return;
                
                const mimeType = previewImg.src.split(";")[0].split(":")[1];
                const extension = mimeType === "image/gif" ? "gif" : "png";
                
                const a = document.createElement("a");
                a.href = previewImg.src;
                a.download = `studio_qrcode.${extension}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }

            async function refreshLogs() {
                try {
                    const r = await fetch("/api/analytics");
                    const logs = await r.json();
                    const container = document.getElementById("analytics_box");
                    
                    if (logs.length === 0) {
                        container.innerHTML = `<p class="text-xs text-slate-500 text-center py-4">No logged scans captured yet.</p>`;
                        return;
                    }
                    
                    container.innerHTML = logs.map(l => `
                        <div class="bg-slate-900 border border-slate-800 p-2.5 rounded text-xs space-y-1">
                            <div class="flex justify-between font-semibold">
                                <span class="text-indigo-400">ID: ${l.qr_id}</span>
                                <span class="text-slate-500">${l.timestamp}</span>
                            </div>
                            <div class="text-slate-400 flex justify-between">
                                <span>Platform: <span class="text-slate-200">${l.device}</span></span>
                                <span>Country: <span class="text-slate-200">${l.country}</span></span>
                            </div>
                        </div>
                    `).join('');
                } catch(e) {}
            }

            setInterval(refreshLogs, 4000);
            togglePayloadFields();
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    # Bound to 0.0.0.0 to accept connections from other devices (like your mobile phone) over Wi-Fi
    uvicorn.run(app, host="0.0.0.0", port=8000)
