# app.py
# 중학교 2학년 과학: 겉보기 등급, 절대등급, 연주시차 시뮬레이터
# Streamlit Cloud에서 바로 실행 가능
# 특징:
# - 별을 불가사리 모양이 아니라 구형 광원처럼 표현
# - 밝기 차이를 별의 크기보다 빛 번짐, 광채, 중심 밝기로 표현
# - 지상 관측 화면, 10 pc 비교 화면, 연주시차 왕복 애니메이션 포함
# - Gaia Archive TAP API 실제 자료를 보조 활동으로 불러올 수 있음

import io
import json
import math

import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components


# ------------------------------------------------------------
# 기본 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="별의 밝기와 연주시차 시뮬레이터",
    page_icon="⭐",
    layout="wide",
)

GAIA_TAP_SYNC_URL = "https://gea.esac.esa.int/tap-server/tap/sync"

# 태양의 절대등급에 가까운 값. 수업용 기준값으로 사용한다.
M_SUN = 4.83

# 실제 밝기 선택지. 1이면 태양과 비슷한 실제 밝기라고 생각한다.
LUMINOSITY_OPTIONS = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1000]


# ------------------------------------------------------------
# 세션 상태 초기화
# ------------------------------------------------------------
DEFAULTS = {
    "a_distance": 5.0,
    "a_luminosity": 0.3,
    "b_distance": 120.0,
    "b_luminosity": 300.0,
    "view_mode": "지구에서 보기",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ------------------------------------------------------------
# 계산 함수
# ------------------------------------------------------------
def absolute_magnitude(luminosity: float) -> float:
    """실제 밝기 비율을 절대등급으로 바꾼다."""
    return M_SUN - 2.5 * math.log10(luminosity)


def apparent_magnitude(abs_mag: float, distance_pc: float) -> float:
    """절대등급과 거리로 겉보기 등급을 계산한다."""
    return abs_mag + 5 * math.log10(distance_pc / 10)


def parallax_mas(distance_pc: float) -> float:
    """거리 pc를 연주시차 mas로 바꾼다. 거리(pc) = 1000 / 연주시차(mas)."""
    return 1000 / distance_pc


def make_star(distance_pc: float, luminosity: float) -> dict:
    """별 하나의 계산값을 정리한다."""
    distance_pc = float(distance_pc)
    luminosity = float(luminosity)
    abs_mag = absolute_magnitude(luminosity)
    app_mag = apparent_magnitude(abs_mag, distance_pc)

    return {
        "distance": distance_pc,
        "luminosity": luminosity,
        "absolute_mag": abs_mag,
        "apparent_mag": app_mag,
        "parallax_mas": parallax_mas(distance_pc),
        # 화면 표현용 밝기 지수. 실제 관측 단위가 아니라 비교용이다.
        "apparent_flux": luminosity / (distance_pc**2),
        "absolute_flux": luminosity / (10**2),
    }


def mag_ratio(mag1: float, mag2: float) -> float:
    """등급 차이를 밝기 비율로 바꾼다. 등급 5 차이는 밝기 100배 차이다."""
    return 10 ** (abs(mag1 - mag2) / 2.5)


def compare_mag(mag_a: float, mag_b: float, name_a="별 A", name_b="별 B"):
    """등급 숫자가 작을수록 더 밝다."""
    if abs(mag_a - mag_b) < 0.05:
        return "거의 같음", f"{name_a}와 {name_b}의 밝기는 거의 비슷합니다."

    ratio = mag_ratio(mag_a, mag_b)
    if mag_a < mag_b:
        return name_a, f"{name_a}가 {name_b}보다 약 {ratio:.1f}배 밝습니다."
    return name_b, f"{name_b}가 {name_a}보다 약 {ratio:.1f}배 밝습니다."


def nearest_value(options, value):
    """선택지 중 입력값과 가장 가까운 값을 찾는다."""
    return min(options, key=lambda x: abs(x - value))


def set_preset(a_distance, a_luminosity, b_distance, b_luminosity, mode="지구에서 보기"):
    """버튼으로 실험 조건을 빠르게 바꾼다."""
    st.session_state.a_distance = float(a_distance)
    st.session_state.a_luminosity = float(a_luminosity)
    st.session_state.b_distance = float(b_distance)
    st.session_state.b_luminosity = float(b_luminosity)
    st.session_state.view_mode = mode


# ------------------------------------------------------------
# Canvas 애니메이션
# ------------------------------------------------------------
def render_animation(star_a: dict, star_b: dict, view_mode: str):
    """
    HTML Canvas 기반 실시간 애니메이션을 Streamlit에 삽입한다.
    HTML/JS는 Streamlit의 components.html 안에서 실행된다.
    """

    params = {
        "mode": view_mode,
        "a": star_a,
        "b": star_b,
    }

    html = r'''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<style>
html, body {
    margin: 0;
    padding: 0;
    background: transparent;
    overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "Noto Sans KR", "Segoe UI", sans-serif;
}
.sim-shell {
    width: 100%;
    height: 720px;
    border-radius: 28px;
    overflow: hidden;
    background:
        radial-gradient(circle at 20% 20%, rgba(96,165,250,0.25), transparent 20%),
        radial-gradient(circle at 80% 10%, rgba(168,85,247,0.22), transparent 24%),
        linear-gradient(135deg, #020617 0%, #111827 45%, #1e1b4b 100%);
    box-shadow: 0 24px 70px rgba(15, 23, 42, 0.35);
    position: relative;
}
#canvas {
    width: 100%;
    height: 720px;
    display: block;
}
.badge {
    position: absolute;
    left: 24px;
    top: 22px;
    padding: 10px 14px;
    border-radius: 999px;
    color: #e0f2fe;
    background: rgba(15,23,42,0.65);
    border: 1px solid rgba(255,255,255,0.16);
    font-size: 14px;
    font-weight: 800;
    backdrop-filter: blur(12px);
}
.tip {
    position: absolute;
    left: 24px;
    bottom: 22px;
    max-width: 710px;
    padding: 14px 16px;
    border-radius: 18px;
    color: #dbeafe;
    background: rgba(15,23,42,0.68);
    border: 1px solid rgba(255,255,255,0.16);
    font-size: 15px;
    line-height: 1.5;
    backdrop-filter: blur(12px);
}
</style>
</head>
<body>
<div class="sim-shell">
    <div class="badge" id="modeBadge"></div>
    <canvas id="canvas"></canvas>
    <div class="tip">
        <b>관찰 포인트</b> · 별을 크게 그려서 밝기를 표현하지 않고, 중심 밝기와 주변의 뿌연 광채로 밝기를 표현했습니다.
        가까운 별은 실제로 어두워도 밝게 보일 수 있고, 실제로 매우 밝은 별도 멀리 있으면 어둡게 보일 수 있습니다.
    </div>
</div>

<script>
const P = __PARAMS__;

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const badge = document.getElementById("modeBadge");

let W = 1200;
let H = 720;
const DPR = Math.min(window.devicePixelRatio || 1, 2);

function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    W = rect.width;
    H = rect.height;
    canvas.width = W * DPR;
    canvas.height = H * DPR;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
}
resizeCanvas();
window.addEventListener("resize", resizeCanvas);

const bgStars = Array.from({length: 140}, () => ({
    x: Math.random(),
    y: Math.random(),
    r: 0.45 + Math.random() * 1.4,
    tw: Math.random() * Math.PI * 2,
    speed: 0.6 + Math.random() * 1.5
}));

function clamp(v, min, max) {
    return Math.max(min, Math.min(max, v));
}
function lerp(a, b, t) {
    return a + (b - a) * t;
}
function smoothstep(t) {
    t = clamp(t, 0, 1);
    return t * t * (3 - 2 * t);
}
function distanceToX(distance) {
    const d = clamp(distance, 1, 500);
    const left = 84;
    const right = W * 0.62;
    const ratio = Math.log10(d) / Math.log10(500);
    return left + (right - left) * ratio;
}
function drawRoundRect(x, y, w, h, r, fill, stroke = null) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    if (stroke) {
        ctx.strokeStyle = stroke;
        ctx.lineWidth = 1;
        ctx.stroke();
    }
}
function drawText(text, x, y, size = 14, color = "#e5e7eb", weight = "500", align = "left") {
    ctx.font = `${weight} ${size}px -apple-system, BlinkMacSystemFont, "Noto Sans KR", Segoe UI, sans-serif`;
    ctx.fillStyle = color;
    ctx.textAlign = align;
    ctx.textBaseline = "middle";
    ctx.fillText(text, x, y);
}

// ------------------------------------------------------------
// 구형 광원 표현
// ------------------------------------------------------------
const COLOR_A = {
    outer: "rgba(250, 204, 21, __A__)",
    inner: "rgba(255, 236, 179, __A__)",
    coreWhite: "rgba(255, 255, 255, __A__)",
    coreMid: "rgba(255, 244, 200, __A__)",
    coreEdge: "rgba(255, 220, 120, __A__)"
};
const COLOR_B = {
    outer: "rgba(96, 165, 250, __A__)",
    inner: "rgba(191, 219, 254, __A__)",
    coreWhite: "rgba(255, 255, 255, __A__)",
    coreMid: "rgba(220, 235, 255, __A__)",
    coreEdge: "rgba(170, 205, 255, __A__)"
};
function rgba(template, alpha) {
    return template.replace("__A__", clamp(alpha, 0, 1).toFixed(3));
}
function visualAppearance(flux, maxFlux) {
    const ratio = Math.sqrt(clamp(flux / maxFlux, 0.0005, 1));
    return {
        coreR: 8.5,
        innerGlowR: 16 + 9 * ratio,
        outerGlowR: 34 + 90 * ratio,
        coreAlpha: 0.72 + 0.28 * ratio,
        haloAlpha: 0.06 + 0.46 * ratio,
        ratio: ratio
    };
}
function drawLightOrb(x, y, appearance, colorSet) {
    const coreR = appearance.coreR;
    const innerGlowR = appearance.innerGlowR;
    const outerGlowR = appearance.outerGlowR;
    const coreAlpha = appearance.coreAlpha;
    const haloAlpha = appearance.haloAlpha;

    const g1 = ctx.createRadialGradient(x, y, 0, x, y, outerGlowR);
    g1.addColorStop(0, rgba(colorSet.outer, haloAlpha * 0.95));
    g1.addColorStop(0.28, rgba(colorSet.outer, haloAlpha * 0.52));
    g1.addColorStop(0.65, rgba(colorSet.outer, haloAlpha * 0.17));
    g1.addColorStop(1, rgba(colorSet.outer, 0));
    ctx.beginPath();
    ctx.arc(x, y, outerGlowR, 0, Math.PI * 2);
    ctx.fillStyle = g1;
    ctx.fill();

    const g2 = ctx.createRadialGradient(x, y, 0, x, y, innerGlowR);
    g2.addColorStop(0, rgba(colorSet.inner, 0.45 + haloAlpha * 0.75));
    g2.addColorStop(0.48, rgba(colorSet.inner, 0.18 + haloAlpha * 0.35));
    g2.addColorStop(1, rgba(colorSet.inner, 0));
    ctx.beginPath();
    ctx.arc(x, y, innerGlowR, 0, Math.PI * 2);
    ctx.fillStyle = g2;
    ctx.fill();

    const g3 = ctx.createRadialGradient(x - coreR * 0.28, y - coreR * 0.28, 1, x, y, coreR);
    g3.addColorStop(0, rgba(colorSet.coreWhite, Math.min(1, coreAlpha + 0.1)));
    g3.addColorStop(0.38, rgba(colorSet.coreMid, coreAlpha));
    g3.addColorStop(1, rgba(colorSet.coreEdge, coreAlpha * 0.9));
    ctx.beginPath();
    ctx.arc(x, y, coreR, 0, Math.PI * 2);
    ctx.fillStyle = g3;
    ctx.fill();

    ctx.beginPath();
    ctx.arc(x - coreR * 0.22, y - coreR * 0.22, coreR * 0.22, 0, Math.PI * 2);
    ctx.fillStyle = rgba(colorSet.coreWhite, coreAlpha * 0.75);
    ctx.fill();
}

function drawEarth(x, y) {
    const g = ctx.createRadialGradient(x - 10, y - 12, 5, x, y, 38);
    g.addColorStop(0, "#bfdbfe");
    g.addColorStop(0.35, "#3b82f6");
    g.addColorStop(0.7, "#2563eb");
    g.addColorStop(1, "#0f172a");

    ctx.save();
    ctx.shadowColor = "#60a5fa";
    ctx.shadowBlur = 28;
    ctx.beginPath();
    ctx.arc(x, y, 38, 0, Math.PI * 2);
    ctx.fillStyle = g;
    ctx.fill();
    ctx.restore();

    ctx.beginPath();
    ctx.arc(x - 8, y - 5, 12, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(34,197,94,0.75)";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(x + 13, y + 11, 10, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(34,197,94,0.65)";
    ctx.fill();
    drawText("지구", x, y + 58, 15, "#bfdbfe", "800", "center");
}

function drawMainScene(t) {
    const isAbs = P.mode === "10 pc로 옮겨 보기";
    const earthX = 72;
    const earthY = H * 0.52;
    const yA = H * 0.36;
    const yB = H * 0.61;
    const x10 = distanceToX(10);
    const xA0 = distanceToX(P.a.distance);
    const xB0 = distanceToX(P.b.distance);

    const moveT = isAbs ? smoothstep(clamp((t - 0.25) / 2.2, 0, 1)) : 0;
    const xA = lerp(xA0, x10, moveT);
    const xB = lerp(xB0, x10, moveT);

    const fluxA = isAbs ? P.a.absolute_flux : P.a.apparent_flux;
    const fluxB = isAbs ? P.b.absolute_flux : P.b.apparent_flux;
    const maxFlux = Math.max(fluxA, fluxB);
    const appA = visualAppearance(fluxA, maxFlux);
    const appB = visualAppearance(fluxB, maxFlux);

    ctx.strokeStyle = "rgba(191,219,254,0.28)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(earthX, earthY);
    ctx.lineTo(W * 0.66, earthY);
    ctx.stroke();

    [1, 10, 100, 500].forEach(d => {
        const x = distanceToX(d);
        ctx.strokeStyle = d === 10 ? "rgba(251,191,36,0.95)" : "rgba(255,255,255,0.22)";
        ctx.lineWidth = d === 10 ? 2 : 1;
        ctx.beginPath();
        ctx.moveTo(x, earthY - 105);
        ctx.lineTo(x, earthY + 125);
        ctx.stroke();
        drawText(`${d} pc`, x, earthY + 150, 13, d === 10 ? "#fde68a" : "#bfdbfe", "700", "center");
    });

    drawRoundRect(x10 - 44, earthY - 143, 88, 30, 15, "rgba(251,191,36,0.18)", "rgba(251,191,36,0.65)");
    drawText("10 pc 기준", x10, earthY - 128, 13, "#fde68a", "900", "center");

    drawEarth(earthX, earthY);

    ctx.setLineDash([6, 8]);
    ctx.strokeStyle = "rgba(147,197,253,0.27)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(earthX + 35, earthY - 5);
    ctx.lineTo(xA, yA);
    ctx.moveTo(earthX + 35, earthY + 5);
    ctx.lineTo(xB, yB);
    ctx.stroke();
    ctx.setLineDash([]);

    drawLightOrb(xA, yA, appA, COLOR_A);
    drawLightOrb(xB, yB, appB, COLOR_B);

    drawRoundRect(xA - 55, yA - 54, 110, 30, 15, "rgba(15,23,42,0.72)", "rgba(255,255,255,0.16)");
    drawText("별 A", xA, yA - 39, 14, "#fde68a", "900", "center");
    drawRoundRect(xB - 55, yB + 24, 110, 30, 15, "rgba(15,23,42,0.72)", "rgba(255,255,255,0.16)");
    drawText("별 B", xB, yB + 39, 14, "#bfdbfe", "900", "center");

    const title = isAbs
        ? "절대등급 모드 · 두 별을 같은 거리 10 pc에 놓고 비교"
        : "겉보기 모드 · 지구에서 실제로 보이는 밝기";
    const sub = isAbs
        ? "거리 효과를 제거하면 별 자체의 밝기 차이가 드러납니다."
        : "가까운 별은 실제로 어두워도 밝게 보일 수 있습니다.";
    drawText(title, 26, 70, 24, "#f8fafc", "900");
    drawText(sub, 28, 102, 15, "#cbd5e1", "600");

    const cardX = 28;
    const cardY = 130;
    drawRoundRect(cardX, cardY, 310, 118, 18, "rgba(15,23,42,0.58)", "rgba(255,255,255,0.13)");
    drawText("별 A", cardX + 20, cardY + 26, 15, "#fde68a", "900");
    drawText(`거리 ${P.a.distance.toFixed(0)} pc · 연주시차 ${P.a.parallax_mas.toFixed(1)} mas`, cardX + 20, cardY + 55, 14, "#e2e8f0", "600");
    drawText(`겉보기등급 ${P.a.apparent_mag.toFixed(2)} · 절대등급 ${P.a.absolute_mag.toFixed(2)}`, cardX + 20, cardY + 84, 14, "#e2e8f0", "600");

    drawRoundRect(cardX, cardY + 132, 310, 118, 18, "rgba(15,23,42,0.58)", "rgba(255,255,255,0.13)");
    drawText("별 B", cardX + 20, cardY + 158, 15, "#bfdbfe", "900");
    drawText(`거리 ${P.b.distance.toFixed(0)} pc · 연주시차 ${P.b.parallax_mas.toFixed(1)} mas`, cardX + 20, cardY + 187, 14, "#e2e8f0", "600");
    drawText(`겉보기등급 ${P.b.apparent_mag.toFixed(2)} · 절대등급 ${P.b.absolute_mag.toFixed(2)}`, cardX + 20, cardY + 216, 14, "#e2e8f0", "600");
}

function drawParallaxPanel(t) {
    const x = W * 0.69;
    const y = 42;
    const w = W * 0.285;
    const h = 235;
    drawRoundRect(x, y, w, h, 22, "rgba(15,23,42,0.64)", "rgba(255,255,255,0.16)");
    drawText("연주시차 애니메이션", x + 22, y + 28, 18, "#f8fafc", "900");
    drawText("가까운 별일수록 배경별에 대해 더 크게 왕복합니다.", x + 22, y + 56, 13, "#cbd5e1", "600");

    for (let i = 0; i < 40; i++) {
        const px = x + 22 + ((i * 73) % (w - 44));
        const py = y + 82 + ((i * 41) % (h - 112));
        ctx.beginPath();
        ctx.arc(px, py, 1.05, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(226,232,240,0.35)";
        ctx.fill();
    }

    const maxP = Math.max(P.a.parallax_mas, P.b.parallax_mas);
    const ampA = 8 + 70 * (P.a.parallax_mas / maxP);
    const ampB = 8 + 70 * (P.b.parallax_mas / maxP);
    const centerX = x + w * 0.55;
    const yA = y + 122;
    const yB = y + 174;
    const wobble = Math.sin(t * 1.75);
    const xa = centerX + ampA * wobble;
    const xb = centerX + ampB * wobble;

    ctx.strokeStyle = "rgba(255,255,255,0.18)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 7]);
    ctx.beginPath();
    ctx.moveTo(centerX, y + 86);
    ctx.lineTo(centerX, y + h - 22);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.strokeStyle = "rgba(250,204,21,0.28)";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(centerX - ampA, yA);
    ctx.lineTo(centerX + ampA, yA);
    ctx.stroke();

    ctx.strokeStyle = "rgba(96,165,250,0.28)";
    ctx.beginPath();
    ctx.moveTo(centerX - ampB, yB);
    ctx.lineTo(centerX + ampB, yB);
    ctx.stroke();

    const smallOrb = {coreR: 5.5, innerGlowR: 12, outerGlowR: 23, coreAlpha: 0.95, haloAlpha: 0.32};
    drawLightOrb(xa, yA, smallOrb, COLOR_A);
    drawLightOrb(xb, yB, smallOrb, COLOR_B);

    drawText(`별 A · ${P.a.parallax_mas.toFixed(1)} mas`, x + 24, yA, 13, "#fde68a", "800");
    drawText(`별 B · ${P.b.parallax_mas.toFixed(1)} mas`, x + 24, yB, 13, "#bfdbfe", "800");
    drawText("※ 실제 각도보다 과장해서 표현한 모형", x + 22, y + h - 22, 12, "#94a3b8", "600");
}

function drawMiniSkyBox(title, x, y, w, h, fluxA, fluxB, label) {
    drawRoundRect(x, y, w, h, 22, "rgba(15,23,42,0.64)", "rgba(255,255,255,0.16)");
    drawText(title, x + 20, y + 27, 17, "#f8fafc", "900");
    drawText(label, x + 20, y + 53, 12, "#cbd5e1", "600");

    const skyX = x + 18;
    const skyY = y + 72;
    const skyW = w - 36;
    const skyH = h - 92;
    const g = ctx.createLinearGradient(skyX, skyY, skyX, skyY + skyH);
    g.addColorStop(0, "#020617");
    g.addColorStop(1, "#172554");
    drawRoundRect(skyX, skyY, skyW, skyH, 16, g, "rgba(255,255,255,0.10)");

    for (let i = 0; i < 28; i++) {
        const px = skyX + 12 + ((i * 47) % (skyW - 24));
        const py = skyY + 12 + ((i * 29) % (skyH - 24));
        ctx.beginPath();
        ctx.arc(px, py, 0.75, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255,255,255,0.25)";
        ctx.fill();
    }

    const maxF = Math.max(fluxA, fluxB);
    const appA = visualAppearance(fluxA, maxF);
    const appB = visualAppearance(fluxB, maxF);
    const miniA = {coreR: 6.5, innerGlowR: appA.innerGlowR * 0.50, outerGlowR: appA.outerGlowR * 0.42, coreAlpha: appA.coreAlpha, haloAlpha: appA.haloAlpha};
    const miniB = {coreR: 6.5, innerGlowR: appB.innerGlowR * 0.50, outerGlowR: appB.outerGlowR * 0.42, coreAlpha: appB.coreAlpha, haloAlpha: appB.haloAlpha};
    const ax = skyX + skyW * 0.35;
    const bx = skyX + skyW * 0.66;
    const sy = skyY + skyH * 0.53;
    drawLightOrb(ax, sy, miniA, COLOR_A);
    drawLightOrb(bx, sy, miniB, COLOR_B);
    drawText("A", ax, skyY + skyH - 18, 13, "#fde68a", "900", "center");
    drawText("B", bx, skyY + skyH - 18, 13, "#bfdbfe", "900", "center");
}

function drawMiniPanels() {
    const x = W * 0.69;
    const y = 300;
    const w = W * 0.285;
    const h = 172;
    drawMiniSkyBox("지상 관측 화면", x, y, w, h, P.a.apparent_flux, P.b.apparent_flux, "현재 거리에서 지구가 보는 밝기");
    drawMiniSkyBox("10 pc 비교 화면", x, y + 192, w, h, P.a.absolute_flux, P.b.absolute_flux, "거리 조건을 같게 만든 밝기");
}

function drawBackground(t) {
    const grad = ctx.createLinearGradient(0, 0, W, H);
    grad.addColorStop(0, "#020617");
    grad.addColorStop(0.45, "#111827");
    grad.addColorStop(1, "#1e1b4b");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    bgStars.forEach(s => {
        const twinkle = 0.35 + 0.65 * Math.abs(Math.sin(t * s.speed + s.tw));
        ctx.beginPath();
        ctx.arc(s.x * W, s.y * H, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${0.18 + 0.5 * twinkle})`;
        ctx.fill();
    });
}

const start = performance.now();
function animate(now) {
    const t = (now - start) / 1000;
    drawBackground(t);
    drawMainScene(t);
    drawParallaxPanel(t);
    drawMiniPanels();
    badge.textContent = P.mode === "10 pc로 옮겨 보기" ? "🚀 절대등급 모드" : "👀 겉보기 모드";
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
</script>
</body>
</html>
'''

    html = html.replace("__PARAMS__", json.dumps(params, ensure_ascii=False))
    components.html(html, height=720, scrolling=False)


# ------------------------------------------------------------
# Gaia 실제 자료 불러오기
# ------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_gaia_data():
    """Gaia Archive TAP API에서 실제 별 자료를 불러온다."""
    candidate_tables = ["gaiadr3.gaia_source_lite", "gaiadr3.gaia_source"]
    last_error = None

    for table_name in candidate_tables:
        query = f"""
        SELECT TOP 100
            source_id,
            ra,
            dec,
            parallax,
            parallax_error,
            phot_g_mean_mag,
            bp_rp
        FROM {table_name}
        WHERE
            parallax IS NOT NULL
            AND parallax > 1
            AND parallax_error IS NOT NULL
            AND parallax / parallax_error > 20
            AND phot_g_mean_mag IS NOT NULL
            AND phot_g_mean_mag < 12
        ORDER BY phot_g_mean_mag ASC
        """

        payload = {
            "REQUEST": "doQuery",
            "LANG": "ADQL",
            "FORMAT": "csv",
            "QUERY": query,
        }

        try:
            response = requests.post(GAIA_TAP_SYNC_URL, data=payload, timeout=60)
            response.raise_for_status()
            text = response.text.strip()

            if text.startswith("<"):
                raise RuntimeError("Gaia Archive에서 CSV가 아닌 응답을 받았습니다.")

            df = pd.read_csv(io.StringIO(text))
            df.columns = [c.strip().lower() for c in df.columns]

            for col in ["ra", "dec", "parallax", "parallax_error", "phot_g_mean_mag", "bp_rp"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            df = df.dropna(subset=["parallax", "phot_g_mean_mag"]).copy()
            df = df[df["parallax"] > 0]
            df["distance_pc"] = 1000 / df["parallax"]
            df["absolute_g_mag"] = df["phot_g_mean_mag"] + 5 - 5 * np.log10(df["distance_pc"])
            df["luminosity_like"] = 10 ** ((M_SUN - df["absolute_g_mag"]) / 2.5)
            df = df.reset_index(drop=True)
            df["번호"] = df.index + 1

            if len(df) >= 2:
                return df, table_name

        except Exception as e:
            last_error = e

    raise RuntimeError(f"Gaia 자료를 불러오지 못했습니다: {last_error}")


# ------------------------------------------------------------
# 상단 화면
# ------------------------------------------------------------
st.title("⭐ 별의 밝기와 연주시차 시뮬레이터")
st.caption("중학교 2학년 과학 · 겉보기 등급 · 절대등급 · 연주시차")

st.markdown(
    """
이 앱은 별의 **거리**와 **실제 밝기**를 직접 조작하면서  
왜 **보이는 밝기와 실제 밝기**가 달라질 수 있는지 확인하는 수업용 시뮬레이터입니다.

별은 크기를 키워서 표현하지 않고, **구형 광원 주변의 뿌연 빛 번짐**으로 밝기를 표현했습니다.
"""
)


# ------------------------------------------------------------
# 빠른 실험 장면
# ------------------------------------------------------------
st.subheader("🎬 빠른 실험 장면")
p1, p2, p3, p4 = st.columns(4)

with p1:
    if st.button("가깝고 어두운 별 vs 멀고 밝은 별", use_container_width=True):
        set_preset(5, 0.3, 120, 300, "지구에서 보기")
        st.rerun()

with p2:
    if st.button("같은 실제 밝기, 거리만 다르게", use_container_width=True):
        set_preset(5, 1, 100, 1, "지구에서 보기")
        st.rerun()

with p3:
    if st.button("같은 거리, 실제 밝기만 다르게", use_container_width=True):
        set_preset(50, 0.3, 50, 100, "지구에서 보기")
        st.rerun()

with p4:
    if st.button("연주시차 차이 크게 보기", use_container_width=True):
        set_preset(3, 1, 200, 30, "지구에서 보기")
        st.rerun()


# ------------------------------------------------------------
# 탭 구성
# ------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🌌 시뮬레이터", "📘 수업 질문", "🔭 Gaia 실제 자료"])


# ------------------------------------------------------------
# 탭 1: 시뮬레이터
# ------------------------------------------------------------
with tab1:
    st.subheader("1. 별의 조건을 조작하세요")
    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        st.markdown("### 🟡 별 A")
        st.slider(
            "별 A의 거리(pc)",
            min_value=1.0,
            max_value=500.0,
            step=1.0,
            key="a_distance",
            help="거리가 가까울수록 연주시차가 커지고, 지구에서 더 밝게 보일 수 있습니다.",
        )
        st.select_slider(
            "별 A의 실제 밝기",
            options=LUMINOSITY_OPTIONS,
            key="a_luminosity",
            help="1이면 태양과 비슷한 실제 밝기라고 생각합니다.",
        )

    with c2:
        st.markdown("### 🔵 별 B")
        st.slider(
            "별 B의 거리(pc)",
            min_value=1.0,
            max_value=500.0,
            step=1.0,
            key="b_distance",
            help="거리가 멀수록 연주시차가 작고, 지구에서 어둡게 보일 수 있습니다.",
        )
        st.select_slider(
            "별 B의 실제 밝기",
            options=LUMINOSITY_OPTIONS,
            key="b_luminosity",
            help="1이면 태양과 비슷한 실제 밝기라고 생각합니다.",
        )

    with c3:
        st.markdown("### 👁️ 관찰 모드")
        st.radio("화면 모드", ["지구에서 보기", "10 pc로 옮겨 보기"], key="view_mode")
        st.info(
            "먼저 지구에서 본 다음, 10 pc로 옮겨 보세요. "
            "겉보기 등급과 절대등급의 차이가 더 분명해집니다."
        )

    star_a = make_star(st.session_state.a_distance, st.session_state.a_luminosity)
    star_b = make_star(st.session_state.b_distance, st.session_state.b_luminosity)

    st.divider()
    render_animation(star_a, star_b, st.session_state.view_mode)
    st.divider()

    st.subheader("2. 수치로 확인하기")
    m1, m2 = st.columns(2)

    with m1:
        st.markdown("### 🟡 별 A")
        st.metric("거리", f"{star_a['distance']:.0f} pc")
        st.metric("연주시차", f"{star_a['parallax_mas']:.2f} mas")
        st.metric("겉보기 등급", f"{star_a['apparent_mag']:.2f}")
        st.metric("절대등급", f"{star_a['absolute_mag']:.2f}")

    with m2:
        st.markdown("### 🔵 별 B")
        st.metric("거리", f"{star_b['distance']:.0f} pc")
        st.metric("연주시차", f"{star_b['parallax_mas']:.2f} mas")
        st.metric("겉보기 등급", f"{star_b['apparent_mag']:.2f}")
        st.metric("절대등급", f"{star_b['absolute_mag']:.2f}")

    apparent_winner, apparent_text = compare_mag(
        star_a["apparent_mag"], star_b["apparent_mag"], "별 A", "별 B"
    )
    absolute_winner, absolute_text = compare_mag(
        star_a["absolute_mag"], star_b["absolute_mag"], "별 A", "별 B"
    )

    r1, r2 = st.columns(2)
    with r1:
        st.markdown("### 👀 겉보기 등급 비교")
        st.write(apparent_text)
        st.caption("겉보기 등급은 지구에서 보이는 밝기입니다.")
    with r2:
        st.markdown("### 💡 절대등급 비교")
        st.write(absolute_text)
        st.caption("절대등급은 두 별을 모두 10 pc에 두었다고 생각했을 때의 밝기입니다.")

    if (
        apparent_winner != absolute_winner
        and apparent_winner != "거의 같음"
        and absolute_winner != "거의 같음"
    ):
        st.success(
            f"핵심 발견: 지구에서 볼 때는 {apparent_winner}가 더 밝지만, "
            f"10 pc에서 비교하면 {absolute_winner}가 더 밝습니다. "
            "즉, 보이는 밝기와 실제 밝기는 다를 수 있습니다."
        )
    else:
        st.warning(
            "이번 조건에서는 겉보기 밝기 순서와 실제 밝기 순서가 크게 뒤집히지 않았습니다. "
            "거리와 실제 밝기를 더 극단적으로 바꿔 보세요."
        )


# ------------------------------------------------------------
# 탭 2: 수업 질문
# ------------------------------------------------------------
with tab2:
    st.subheader("📘 학생 탐구 질문")
    st.markdown(
        """
### 활동 1. 겉보기 밝기 관찰하기

1. 별 A와 별 B 중 지구에서 더 밝게 보이는 별은 무엇인가?
2. 더 밝게 보인 이유는 실제로 밝기 때문인가, 거리가 가깝기 때문인가?
3. 별의 거리를 멀게 하면 지상 관측 화면에서 어떤 변화가 생기는가?
4. 이 앱에서 별의 밝기는 별의 크기 차이로 표현되는가, 빛의 번짐 차이로 표현되는가?

---

### 활동 2. 연주시차 관찰하기

1. 연주시차 애니메이션에서 더 크게 좌우로 움직이는 별은 어느 별인가?
2. 그 별은 가까운 별인가, 먼 별인가?
3. 연주시차가 클수록 거리가 어떻게 되는지 한 문장으로 정리하시오.

---

### 활동 3. 절대등급 이해하기

1. 10 pc로 옮겨 보기 모드에서는 두 별이 어느 위치로 이동하는가?
2. 10 pc 비교 화면에서 더 밝게 보이는 별은 어느 별인가?
3. 절대등급은 왜 모든 별을 10 pc에 둔다고 가정할까?
4. 보이는 밝기와 실제 밝기가 다를 수 있는 이유를 설명하시오.

---

### 학생 정리 문장

- 겉보기 등급은 별이 ________에서 보이는 밝기를 나타낸다.
- 절대등급은 별을 모두 ________ pc에 두었다고 생각했을 때의 밝기이다.
- 연주시차가 큰 별은 거리가 ________ 별이다.
- 별이 밝게 보인다고 해서 반드시 실제로 밝은 것은 아니다. 왜냐하면 ________ 때문이다.
"""
    )
    st.info(
        "수업에서는 수식보다 먼저 화면 조작을 시키는 것이 좋습니다. "
        "학생이 먼저 '가까우면 밝게 보인다'를 발견한 뒤, "
        "그다음 절대등급과 10 pc의 의미를 설명하면 이해가 더 쉽습니다."
    )


# ------------------------------------------------------------
# 탭 3: Gaia 실제 자료
# ------------------------------------------------------------
with tab3:
    st.subheader("🔭 Gaia 실제 별 자료로 확인하기")
    st.markdown(
        """
이 탭은 실제 관측 자료를 시뮬레이터에 넣어 보는 보조 활동입니다.  
수업 도입에서는 먼저 시뮬레이터로 개념을 잡고, 이후 실제 자료로 확장하는 흐름이 좋습니다.
"""
    )

    try:
        with st.spinner("Gaia Archive에서 실제 별 자료를 불러오는 중입니다..."):
            gaia_df, used_table = load_gaia_data()

        st.success(f"Gaia 실제 별 자료 {len(gaia_df)}개를 불러왔습니다. 사용 테이블: {used_table}")

        def label(row):
            return (
                f"{int(row['번호'])}번 | Gaia {str(row['source_id'])} | "
                f"거리 {row['distance_pc']:.1f} pc | "
                f"겉보기 G {row['phot_g_mean_mag']:.2f} | "
                f"절대 G {row['absolute_g_mag']:.2f}"
            )

        labels = [label(row) for _, row in gaia_df.iterrows()]
        label_to_idx = {v: i for i, v in enumerate(labels)}

        g1, g2 = st.columns(2)
        with g1:
            selected_a = st.selectbox("실제 별 A", labels, index=0)
        with g2:
            selected_b = st.selectbox("실제 별 B", labels, index=1)

        gaia_a = gaia_df.iloc[label_to_idx[selected_a]]
        gaia_b = gaia_df.iloc[label_to_idx[selected_b]]

        show_df = pd.DataFrame(
            [
                {
                    "구분": "실제 별 A",
                    "Gaia source_id": str(gaia_a["source_id"]),
                    "연주시차(mas)": round(float(gaia_a["parallax"]), 3),
                    "거리(pc)": round(float(gaia_a["distance_pc"]), 2),
                    "겉보기 등급 G": round(float(gaia_a["phot_g_mean_mag"]), 2),
                    "절대등급 G": round(float(gaia_a["absolute_g_mag"]), 2),
                },
                {
                    "구분": "실제 별 B",
                    "Gaia source_id": str(gaia_b["source_id"]),
                    "연주시차(mas)": round(float(gaia_b["parallax"]), 3),
                    "거리(pc)": round(float(gaia_b["distance_pc"]), 2),
                    "겉보기 등급 G": round(float(gaia_b["phot_g_mean_mag"]), 2),
                    "절대등급 G": round(float(gaia_b["absolute_g_mag"]), 2),
                },
            ]
        )
        st.dataframe(show_df, use_container_width=True, hide_index=True)

        _, gaia_app_text = compare_mag(
            float(gaia_a["phot_g_mean_mag"]),
            float(gaia_b["phot_g_mean_mag"]),
            "실제 별 A",
            "실제 별 B",
        )
        _, gaia_abs_text = compare_mag(
            float(gaia_a["absolute_g_mag"]),
            float(gaia_b["absolute_g_mag"]),
            "실제 별 A",
            "실제 별 B",
        )

        cga1, cga2 = st.columns(2)
        with cga1:
            st.markdown("### 👀 실제 자료의 겉보기 등급")
            st.write(gaia_app_text)
        with cga2:
            st.markdown("### 💡 실제 자료의 절대등급")
            st.write(gaia_abs_text)

        if st.button("선택한 Gaia 별을 시뮬레이터에 넣기", use_container_width=True):
            st.session_state.a_distance = float(np.clip(gaia_a["distance_pc"], 1, 500))
            st.session_state.b_distance = float(np.clip(gaia_b["distance_pc"], 1, 500))
            st.session_state.a_luminosity = nearest_value(
                LUMINOSITY_OPTIONS,
                float(np.clip(gaia_a["luminosity_like"], 0.01, 1000)),
            )
            st.session_state.b_luminosity = nearest_value(
                LUMINOSITY_OPTIONS,
                float(np.clip(gaia_b["luminosity_like"], 0.01, 1000)),
            )
            st.session_state.view_mode = "지구에서 보기"
            st.rerun()

    except Exception as e:
        st.error("Gaia Archive 자료를 불러오지 못했습니다.")
        st.code(str(e))
        st.info(
            "Gaia 서버 상태나 네트워크 문제일 수 있습니다. "
            "시뮬레이터 탭은 Gaia 연결 없이도 정상 작동합니다."
        )
