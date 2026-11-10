import base64
import json
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from utils.common import header
from utils.parts_catalog import IMAGE_PART_CODES, PART_CATALOG


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "parts"
MANIFEST_PATH = ASSET_DIR / "archive_manifest.json"


def _image_data_uri(path):
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _build_guide_html():
    manifest = json.loads(MANIFEST_PATH.read_text())
    zip_images = {}
    for row in manifest:
        row["image"] = _image_data_uri(ASSET_DIR / row["path"])
        zip_images.setdefault(row["hscd"], []).append(row)

    guide_items = []
    for item in PART_CATALOG:
        code = item["hscd"]
        image_code = item.get("image_code", code)
        images = zip_images.get(image_code, [])
        image_label = item.get("image_label")
        if image_label:
            images = [photo for photo in images if photo["label"] == image_label]
        if not images:
            images = [{
                "label": item["hsnamekor"],
                "image": _image_data_uri(ASSET_DIR / item["ai_image"]),
                "source": "ai",
            }]
        guide_items.append({
            **item,
            "images": images,
            "is_image_part_list": code in IMAGE_PART_CODES,
        })

    items_json = json.dumps(guide_items, ensure_ascii=False).replace("</", "<\\/")
    markers = []
    grouped_list = {item["group"]: [] for item in PART_CATALOG}
    for index, item in enumerate(guide_items, start=1):
        for x, y in item["points"]:
            label = item["hsnamekor"] if not item["is_image_part_list"] else item["hscd"]
            markers.append(
                f'<button class="hotspot" style="left:{x}%;top:{y}%" '
                f'data-code="{item["hscd"]}" title="{escape(label, quote=True)}" '
                f'aria-label="{escape(label, quote=True)} 위치 보기">{index:02}</button>'
            )
        if item["is_image_part_list"]:
            child_buttons = []
            for image_index, photo in enumerate(item["images"]):
                child_buttons.append(
                    f'<button class="part-chip" data-code="{item["hscd"]}" '
                    f'data-image-index="{image_index}"><span>{escape(photo["label"])}</span>'
                    f'<small>#{index:02} · {item["hscd"]}</small></button>'
                )
            grouped_list[item["group"]].append(
                f'<details class="code-section"><summary>{item["hscd"]} · 세부 부품 {len(child_buttons)}개</summary>'
                f'<div class="chips">{"".join(child_buttons)}</div></details>'
            )
        else:
            grouped_list[item["group"]].append(
                f'<button class="part-chip" data-code="{item["hscd"]}">'
                f'<span>{escape(item["hsnamekor"])}</span>'
                f'<small>#{index:02} · {item["hscd"]}</small></button>'
            )
    list_sections = [
        f'<section class="system-section"><h4 class="group-title">{name}</h4>'
        f'<div class="chips">{"".join(entries)}</div></section>'
        for name, entries in grouped_list.items()
        if entries
    ]

    template = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;color:#272b30;font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}
.guide{--accent:#216c68;--line:#d8ddda}.intro{margin:0 0 14px;color:#69716f;font-size:14px;line-height:1.55}
.map-wrap{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:16px;background:#eeece8}.map{position:relative;width:100%;aspect-ratio:2/1;overflow:hidden}.map img{display:block;width:100%;height:100%;object-fit:cover}
.hotspot{position:absolute;z-index:2;display:grid;place-items:center;width:30px;height:30px;padding:0;border:2px solid white;border-radius:50%;background:var(--accent);color:white;box-shadow:0 2px 12px #152d2b55;font-size:10px;font-weight:750;cursor:pointer;transform:translate(-50%,-50%);transition:transform .15s,background .15s}.hotspot:hover,.hotspot:focus-visible{z-index:4;background:#154e4b;outline:3px solid #ffffffa8;transform:translate(-50%,-50%) scale(1.18)}
.map-label{position:absolute;left:14px;bottom:12px;padding:7px 10px;border-radius:8px;background:#ffffffdf;color:#555d5b;font-size:12px}.note{display:flex;gap:10px;align-items:flex-start;margin:12px 2px 18px;color:#6a716f;font-size:12px;line-height:1.6}.note strong{flex:0 0 auto;color:#4f5c59}
.list-title{margin:18px 0 0;color:#3e4947;font-size:16px;font-weight:700}.chips{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:12px 0 0}.system-section{grid-column:1/-1}.group-title{margin:14px 0 0;padding-bottom:7px;border-bottom:1px solid var(--line);color:#45504d;font-size:14px;font-weight:700}.code-section{grid-column:1/-1;border:1px solid var(--line);border-radius:12px;padding:12px;background:#fafaf9}.code-section summary{color:#45504d;font-size:13px;font-weight:700;cursor:pointer}.code-section .chips{margin-top:9px}
.part-chip{min-width:0;padding:10px 11px;border:1px solid var(--line);border-radius:10px;background:#fff;color:#333b39;text-align:left;cursor:pointer}.part-chip:hover,.part-chip:focus-visible{border-color:var(--accent);background:#f3f8f6;outline:none}.part-chip span{display:block;overflow:hidden;font-size:13px;font-weight:650;text-overflow:ellipsis;white-space:nowrap}.part-chip small{display:block;margin-top:4px;color:#808885;font-size:10px}
.modal{position:absolute;z-index:10;inset:0;display:none;align-items:center;justify-content:center;padding:18px;background:#17201fcc}.modal.open{display:flex}.dialog{position:relative;width:min(680px,100%);max-height:100%;overflow:auto;border-radius:18px;background:white;box-shadow:0 18px 60px #0004}.dialog-media{display:flex;flex-direction:column;align-items:center;gap:8px;padding:10px 16px;background:transparent}.image-stage{position:relative;display:grid;place-items:center;width:min(100%,380px);min-height:190px}.dialog-img{display:block;width:min(100%,340px);height:auto;max-height:214px;object-fit:contain;background:transparent}.image-nav{position:absolute;z-index:1;top:50%;display:grid;place-items:center;width:34px;height:34px;padding:0;border:1px solid #d8ddda;border-radius:50%;background:#ffffffed;color:#27312e;font-size:23px;line-height:1;cursor:pointer;transform:translateY(-50%)}.image-nav:hover:not(:disabled),.image-nav:focus-visible{border-color:#216c68;background:white;outline:2px solid #216c6840}.image-nav:disabled{opacity:.35;cursor:default}.image-nav.prev{left:0}.image-nav.next{right:0}.image-count{margin:0;color:#58615e;font-size:12px}.image-source{color:#69716f;font-size:11px}.dialog-body{padding:18px 22px 23px}.eyebrow{margin:0 0 6px;color:#74807c;font-size:12px}.title-row{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}.title-row h2{margin:0;font-size:24px}.code{color:#66716d;font-size:14px}.description{margin:13px 0;color:#424b48;line-height:1.65}.detail{margin:9px 0 0;padding:11px 12px;border-radius:10px;background:#f4f6f4;color:#59625f;font-size:13px;line-height:1.6}.detail b{color:#343d3a}.caution{background:#fbf6eb}.close{position:absolute;z-index:1;top:12px;right:12px;width:34px;height:34px;border:0;border-radius:50%;background:#ffffffed;color:#27312e;font-size:21px;cursor:pointer}
@media(max-width:760px){.chips{grid-template-columns:repeat(2,minmax(0,1fr))}.hotspot{width:25px;height:25px;font-size:9px}.map-label{font-size:10px}}
</style></head><body><main class="guide">
<p class="intro">차량의 점을 누르면 부품 설명과 HS 코드를 볼 수 있어요. 부품 이름을 누르면 해당 사진과 설명이 열립니다.</p>
<div class="map-wrap"><div class="map"><img src="__VEHICLE__" alt="부품 위치를 표시한 일반 승용차 측면 컷어웨이">__MARKERS__<span class="map-label">일반 내연기관 승용차 개념도 · 대표 영역</span></div><div class="modal" id="modal" role="dialog" aria-modal="true" aria-labelledby="part-title"><section class="dialog"><button class="close" id="close" aria-label="닫기">×</button><div id="content"></div></section></div></div>
<p class="note"><strong>위치 안내</strong><span>점은 일반 승용차에서 흔히 볼 수 있는 대표 영역입니다. 차종·연식·구동 방식에 따라 위치와 구성은 달라질 수 있습니다. 한 위치로 정하기 어려운 분류는 점 대신 전체 목록에서 확인하세요.</span></p>
<h3 class="list-title">부품 전체 목록</h3><div class="chips">__LIST__</div></main>
<script>
const parts=__ITEMS__,byCode=new Map(parts.map(p=>[p.hscd,p])),modal=document.getElementById('modal'),content=document.getElementById('content');
const mapWrap=document.querySelector('.map-wrap');
let currentPart=null,currentImageIndex=0;
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function openPart(code,imageIndex=0){const p=byCode.get(code);if(!p)return;currentPart=p;currentImageIndex=Math.max(0,Math.min(imageIndex,p.images.length-1));const photo=p.images[currentImageIndex];const title=p.is_image_part_list?photo.label:p.hsnamekor;const source=photo.source==='ai'?'<span class="image-source">AI로 생성한 이미지입니다</span>':'';const navigation=p.images.length>1?`<button class="image-nav prev" data-image-step="-1" aria-label="이전 부품" ${currentImageIndex===0?'disabled':''}>‹</button><button class="image-nav next" data-image-step="1" aria-label="다음 부품" ${currentImageIndex===p.images.length-1?'disabled':''}>›</button>`:'';
content.innerHTML=`<div class="dialog-media"><div class="image-stage"><img class="dialog-img" src="${photo.image}" alt="${esc(title)} 사진">${navigation}</div>${p.images.length>1?`<p class="image-count">${currentImageIndex+1} / ${p.images.length} · ${esc(photo.label)}</p>`:''}${source}</div><div class="dialog-body"><p class="eyebrow">${esc(p.group)}</p><div class="title-row"><h2 id="part-title">${esc(title)}</h2><span class="code">${esc(p.hscd)}</span></div><p class="description">${esc(p.description)}</p><p class="detail"><b>차량 위치</b><br>${esc(p.location)}</p></div>`;
modal.classList.add('open');document.getElementById('close').focus();content.querySelectorAll('[data-image-step]').forEach(button=>button.addEventListener('click',()=>openPart(code,currentImageIndex+Number(button.dataset.imageStep))));}
function closeModal(){modal.classList.remove('open')}
document.querySelectorAll('.hotspot').forEach(button=>button.addEventListener('click',()=>openPart(button.dataset.code)));
document.querySelectorAll('.part-chip').forEach(button=>button.addEventListener('click',()=>{mapWrap.scrollIntoView({behavior:'smooth',block:'center'});openPart(button.dataset.code,Number(button.dataset.imageIndex||0))}));
document.getElementById('close').addEventListener('click',closeModal);modal.addEventListener('click',e=>{if(e.target===modal)closeModal()});document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();if(!modal.classList.contains('open')||!currentPart||currentPart.images.length<2)return;if(e.key==='ArrowLeft'&&currentImageIndex>0)openPart(currentPart.hscd,currentImageIndex-1);if(e.key==='ArrowRight'&&currentImageIndex<currentPart.images.length-1)openPart(currentPart.hscd,currentImageIndex+1)});
</script></body></html>'''
    return (
        template.replace("__VEHICLE__", _image_data_uri(ASSET_DIR / "vehicle-cutaway.jpg"))
        .replace("__MARKERS__", "".join(markers))
        .replace("__LIST__", "".join(list_sections))
        .replace("__ITEMS__", items_json)
    )


def codes_page():
    header("부품 코드 안내", "자동차의 어느 부품을 말하나요?")
    components.html(_build_guide_html(), height=1180, scrolling=True)
