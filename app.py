"""Local browser interface. Run: python -m streamlit run app.py"""
import io
import html
import json
import os
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from quran_reels.renderer import SIZES, check_dependencies, generate
from quran_reels.layout import TEXT_ELEMENTS, VideoStyle, TextStyle, LogoStyle, compose_overlay, load_logo, overlap_warnings, preview_image
from quran_reels.sources import RECITERS, TRANSLATIONS, UserError, fetch_passage, surahs
from quran_reels.desktop import data_directory

ROOT = data_directory()
load_dotenv(ROOT / ".env")
st.set_page_config(page_title="Quran Reels Studio", page_icon="🌙", layout="wide")
st.title("Quran Reels Studio")
st.write("Turn complete Quran ayahs into videos with real recitation, Arabic captions and scenic footage.")
st.caption("Runs on your computer · No AI voice or translation · Your own API keys")


@st.cache_data(ttl=86400, show_spinner=False)
def chapters():
    return surahs()


try:
    check_dependencies()
    catalogue = chapters()
except UserError as error:
    st.error(str(error))
    st.stop()

with st.sidebar:
    st.subheader("Background source")
    provider_label = st.radio("Provider", ["Pexels", "Pixabay", "My own video"])
    provider = provider_label.lower()
    api_key = ""
    upload = None
    if provider_label != "My own video":
        api_key = st.text_input(f"{provider_label} API key", type="password", value=os.getenv(f"{provider_label.upper()}_API_KEY", ""), help="Kept in this local app session. Never included in your export.")
        st.markdown("[Get a Pexels API key](https://www.pexels.com/api/)" if provider == "pexels" else "[Get a Pixabay API key](https://pixabay.com/api/docs/)")
        query = st.text_input("Search for footage", value="mountains nature", max_chars=100)
        st.markdown("Videos provided by [Pexels](https://www.pexels.com)." if provider == "pexels" else "Videos provided by [Pixabay](https://pixabay.com).")
    else:
        query = ""
        upload = st.file_uploader("Upload your footage", type=["mp4", "mov", "mkv", "webm"])
        st.caption("Use a video at least as long as the full recitation. Its original sound is removed.")
    st.divider()
    st.caption("Keys are sent to your chosen stock provider. Quran requests go to AlQuran Cloud. Search responses are cached locally for 24 hours. Generated videos stay in output/ until you delete them.")

left, right = st.columns([1.15, 1], gap="large")
with left:
    st.subheader("1. Choose your passage")
    chapter = st.selectbox("Surah", catalogue, index=111, format_func=lambda item: f"{item['number']}. {item['englishName']} · {item['name']}")
    a, b = st.columns(2)
    start = int(a.number_input("First ayah", min_value=1, max_value=chapter["numberOfAyahs"], value=1))
    end = int(b.number_input("Last ayah", min_value=start, max_value=min(chapter["numberOfAyahs"], start + 11), value=min(chapter["numberOfAyahs"], start + 3)))
    reciter_label = st.selectbox("Reciter", list(RECITERS))
    translation_label = st.selectbox("Translation of the meaning", list(TRANSLATIONS))
    selected_size = st.selectbox("Video format", list(SIZES))
    signature = (chapter["number"], start, end, RECITERS[reciter_label], TRANSLATIONS[translation_label])
    if st.button("Load passage for review", use_container_width=True):
        try:
            with st.spinner("Retrieving Quran text and recitation links…"):
                st.session_state.passage = fetch_passage(*signature)
                st.session_state.signature = signature
        except UserError as error:
            st.error(str(error))
    passage = st.session_state.get("passage") if st.session_state.get("signature") == signature else None
    if passage:
        for verse in passage.verses:
            with st.expander(f"Ayah {verse.reference}", expanded=True):
                st.markdown(f"<div dir='rtl' style='font-size:1.65rem;line-height:2.2'>{html.escape(verse.arabic)}</div>", unsafe_allow_html=True)
                if verse.translation:
                    st.write(verse.translation)
                st.audio(verse.audio_url)
        st.caption(f"Arabic: quran-uthmani · Recitation: {passage.reciter} · Translation: {passage.translation_edition or 'none'} · Source: AlQuran Cloud")

with right:
    st.subheader("2. Design your video")
    st.caption("Show or hide elements and choose their positions. Horizontal: 0 = left, 100 = right. Vertical: 0 = top, 100 = bottom. Elements stay inside the frame.")
    defaults = VideoStyle()
    elements = {}
    for name, label in TEXT_ELEMENTS.items():
        default = getattr(defaults, name)
        with st.expander(label, expanded=False):
            visible = st.checkbox(f"Show {label.lower()}", value=default.visible, key=f"design-{name}-visible")
            columns = st.columns(2)
            x = columns[0].slider("Horizontal position (%)", 0, 100, int(default.x), key=f"design-{name}-x", disabled=not visible)
            y = columns[1].slider("Vertical position (%)", 0, 100, int(default.y), key=f"design-{name}-y", disabled=not visible)
            columns = st.columns(2)
            font_size = columns[0].slider("Text size", 18, 120, default.size, key=f"design-{name}-size", disabled=not visible, help="Scales automatically with the selected video format. Long text may be reduced to fit.")
            width = columns[1].slider("Maximum width (%)", 10, 95, int(default.width), key=f"design-{name}-width", disabled=not visible)
            elements[name] = TextStyle(visible, x, y, width, font_size)
            if name == "watermark":
                watermark_text = st.text_input("Your watermark text", value=defaults.watermark_text, max_chars=120, key="design-watermark-text", disabled=not visible)
    logo_upload = None
    with st.expander("Your logo", expanded=False):
        logo_upload = st.file_uploader("Upload a logo", type=["png", "jpg", "jpeg", "webp"], key="design-logo-file", help="Transparent PNG works well. Maximum 10 MB and 16 million pixels.")
        show_logo = st.checkbox("Show logo", value=True, disabled=logo_upload is None, key="design-logo-visible")
        columns = st.columns(2)
        logo_x = columns[0].slider("Horizontal position (%)", 0, 100, 97, key="design-logo-x")
        logo_y = columns[1].slider("Vertical position (%)", 0, 100, 3, key="design-logo-y")
        columns = st.columns(2)
        logo_width = columns[0].slider("Logo width (%)", 3, 35, 12, key="design-logo-width")
        logo_opacity = columns[1].slider("Logo opacity (%)", 0, 100, 100, key="design-logo-opacity")
    with st.expander("Background and text panels", expanded=False):
        dim = st.slider("Background dimming (%)", 0, 85, defaults.dim, key="design-dim")
        panels = st.checkbox("Show caption panels", value=True, key="design-panels")
    style = VideoStyle(**elements, logo=LogoStyle(bool(logo_upload is not None and show_logo), logo_x, logo_y, logo_width, logo_opacity), watermark_text=watermark_text, dim=dim, panels=panels)
    logo_data = logo_upload.getvalue() if logo_upload is not None and show_logo else None
    layout_valid = True
    st.markdown("**Layout preview**")
    if passage:
        preview_verse = st.selectbox("Preview ayah", passage.verses, format_func=lambda verse: verse.reference, key=f"preview-{signature}")
        try:
            logo = load_logo(logo_data) if logo_data is not None else None
            overlay, boxes = compose_overlay(passage, preview_verse, SIZES[selected_size], style, logo)
            frame = io.BytesIO()
            preview_image(overlay).save(frame, format="PNG")
            st.image(frame.getvalue(), width=360 if SIZES[selected_size][1] > SIZES[selected_size][0] else 700)
            st.caption("Sample background for positioning. The final export uses your selected footage. The preview and export share the same layout.")
            for warning in overlap_warnings(boxes):
                st.warning(warning + " Adjust the positions if this is unintended.")
        except UserError as error:
            st.error(str(error))
            layout_valid = False
    else:
        st.info("Load a passage to preview your design with its actual Quran text.")
    st.download_button("Save layout settings", json.dumps(style.to_dict(), ensure_ascii=False, indent=2), file_name="layout.json", mime="application/json")
    st.subheader("3. Create your video")
    st.write("The background is cropped to fill your chosen format. Captions change at each ayah boundary, using the duration of the downloaded recording.")
    st.info("Long ayahs may not fit a readable caption. If that happens, choose portrait format or turn off the translation. The tool never removes words to make them fit.")
    reviewed = st.checkbox("I have reviewed the selected Arabic text and translation.", key=f"reviewed-{signature}")
    if st.button("Generate video", type="primary", disabled=not passage or not reviewed or not layout_valid, use_container_width=True):
        if provider_label == "My own video" and upload is None:
            st.error("Upload a background video first.")
        elif provider_label != "My own video" and not api_key.strip():
            st.error("Add a stock-video API key or choose your own video.")
        else:
            try:
                with tempfile.TemporaryDirectory(prefix="quran-upload-") as temporary:
                    local_video = None
                    if upload:
                        local_video = Path(temporary) / ("background" + Path(upload.name).suffix.lower())
                        local_video.write_bytes(upload.getbuffer())
                    logo_path = None
                    if logo_data is not None:
                        logo_path = Path(temporary) / "logo-image"
                        logo_path.write_bytes(logo_data)
                    output = ROOT / "output" / f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
                    with st.status("Creating your Quran video…", expanded=True) as status:
                        video = generate(passage, output, size=SIZES[selected_size], provider=provider, key=api_key, query=query, local_video=local_video, style=style, logo_path=logo_path, cache_dir=ROOT / ".cache" / "stock", progress=st.write)
                        status.update(label="Video ready", state="complete", expanded=False)
                    st.session_state.result = str(video)
            except UserError as error:
                st.error(str(error))
            except OSError:
                st.error("Could not write the output. Check disk space and folder permissions.")
    result = st.session_state.get("result")
    if result and Path(result).exists():
        video = Path(result)
        st.caption("Last generated video. Generate again after changing design settings.")
        st.video(str(video))
        st.download_button("Download MP4", video.read_bytes(), file_name="quran-video.mp4", mime="video/mp4", use_container_width=True)
        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in ["video.mp4", "sources.json", "credits.txt", "layout.json"]:
                if (video.parent / name).is_file():
                    archive.write(video.parent / name, arcname=name)
        st.download_button("Download video + sources + layout", bundle.getvalue(), file_name="quran-video.zip", mime="application/zip", use_container_width=True)
        st.caption(f"Saved locally: {video.parent}")
        st.warning("Watch the entire video before publishing. Check the recitation, Quran text, caption readability, background suitability, and rights for the recording and translation.")
        st.text((video.parent / "credits.txt").read_text(encoding="utf-8"))

st.divider()
st.markdown("Made by [TechMouad](https://techmouad.com) · [Source on GitHub](https://github.com/mouad73/quran-reels-studio) · [Quran API](https://alquran.cloud/api)")
