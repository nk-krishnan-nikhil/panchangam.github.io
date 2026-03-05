#!/usr/bin/env python3
"""Generate a Malayalam Panchangam ICS calendar feed.

This script calculates daily Panchangam details using Surya Siddhanta based
formulas and writes a standards-compliant .ics file suitable for Google
Calendar subscription.

Notes:
- The calculation model is deterministic and location-based.
- For best results, set latitude/longitude to your target Kerala location.
"""

from __future__ import annotations

import argparse
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


# Core constants
UJJAIN_LONGITUDE = 75.8
YUGA_ROTATION_STAR = 1582237828
YUGA_ROTATION_SUN = 4320000
YUGA_ROTATION_MOON = 57753336
YUGA_CIVIL_DAYS = YUGA_ROTATION_STAR - YUGA_ROTATION_SUN
SOLAR_APOGEE = 77 + 17 / 60
PI = math.pi
RAD = 180 / PI
EPS = 1e-6
EPSIRON = 1e-8


WEEKDAY_ML = {
    0: "തിങ്കൾ",
    1: "ചൊവ്വ",
    2: "ബുധൻ",
    3: "വ്യാഴം",
    4: "വെള്ളി",
    5: "ശനി",
    6: "ഞായർ",
}

SAURA_MASA_NAMES = {
    0: "Mesa",
    1: "Vrsa",
    2: "Mithuna",
    3: "Karkata",
    4: "Simha",
    5: "Kanya",
    6: "Tula",
    7: "Vrscika",
    8: "Dhanus",
    9: "Makara",
    10: "Kumbha",
    11: "Mina",
}

MALAYALAM_SOLAR_MONTHS = {
    0: ("മേദം", "Medam"),
    1: ("ഇടവം", "Edavam"),
    2: ("മിഥുനം", "Mithunam"),
    3: ("കർക്കടകം", "Karkidakam"),
    4: ("ചിങ്ങം", "Chingam"),
    5: ("കന്നി", "Kanni"),
    6: ("തുലാം", "Thulam"),
    7: ("വൃശ്ചികം", "Vrischikam"),
    8: ("ധനു", "Dhanu"),
    9: ("മകരം", "Makaram"),
    10: ("കുംഭം", "Kumbham"),
    11: ("മീനം", "Meenam"),
}

LUNAR_MASA_NAMES = {
    0: "Caitra",
    1: "Vaisakha",
    2: "Jyaistha",
    3: "Asadha",
    4: "Sravana",
    5: "Bhadrapada",
    6: "Asvina",
    7: "Karttika",
    8: "Margasirsa",
    9: "Pausa",
    10: "Magha",
    11: "Phalguna",
}

LUNAR_MASA_ML = {
    "Caitra": "ചൈത്രം",
    "Vaisakha": "വൈശാഖം",
    "Jyaistha": "ജ്യേഷ്ഠം",
    "Asadha": "ആഷാഢം",
    "Sravana": "ശ്രാവണം",
    "Bhadrapada": "ഭാദ്രപദം",
    "Asvina": "ആശ്വിനം",
    "Karttika": "കാർത്തികം",
    "Margasirsa": "മാർഗശീർഷം",
    "Pausa": "പൗഷം",
    "Magha": "മാഘം",
    "Phalguna": "ഫാൽഗുനം",
}

NAKSHATRA_NAMES = {
    0: "Asvini",
    1: "Bharani",
    2: "Krttika",
    3: "Rohini",
    4: "Mrgasira",
    5: "Ardra",
    6: "Punarvasu",
    7: "Pusya",
    8: "Aslesa",
    9: "Magha",
    10: "P-phalguni",
    11: "U-phalguni",
    12: "Hasta",
    13: "Citra",
    14: "Svati",
    15: "Visakha",
    16: "Anuradha",
    17: "Jyestha",
    18: "Mula",
    19: "P-asadha",
    20: "U-asadha",
    21: "Sravana",
    22: "Dhanistha",
    23: "Satabhisaj",
    24: "P-bhadrapada",
    25: "U-bhadrapada",
    26: "Revati",
    27: "Asvini",
}

NAKSHATRA_ML = {
    "Asvini": "അശ്വതി",
    "Bharani": "ഭരണി",
    "Krttika": "കാർത്തിക",
    "Rohini": "രോഹിണി",
    "Mrgasira": "മകയിരം",
    "Ardra": "തിരുവാതിര",
    "Punarvasu": "പുണർതം",
    "Pusya": "പൂയം",
    "Aslesa": "ആയില്യം",
    "Magha": "മകം",
    "P-phalguni": "പൂരം",
    "U-phalguni": "ഉത്രം",
    "Hasta": "അത്തം",
    "Citra": "ചിത്തിര",
    "Svati": "ചോതി",
    "Visakha": "വിശാഖം",
    "Anuradha": "അനിഴം",
    "Jyestha": "ത്രിക്കേട്ട",
    "Mula": "മൂലം",
    "P-asadha": "പൂരാടം",
    "U-asadha": "ഉത്രാടം",
    "Sravana": "തിരുവോണം",
    "Dhanistha": "അവിറ്റം",
    "Satabhisaj": "ചതയം",
    "P-bhadrapada": "പൂരുരുട്ടാതി",
    "U-bhadrapada": "ഉത്രട്ടാതി",
    "Revati": "രേവതി",
}

YOGA_NAMES = {
    0: "viSkambha",
    1: "prIti",
    2: "AyuSmat",
    3: "saubhAgya",
    4: "zobhana",
    5: "atigaNDa",
    6: "sukarman",
    7: "dhRti",
    8: "zUla",
    9: "gaNDa",
    10: "vRddhi",
    11: "dhruva",
    12: "vyAghAta",
    13: "harSaNa",
    14: "vajra",
    15: "siddhi",
    16: "vyatIpAta",
    17: "varIyas",
    18: "parigha",
    19: "ziva",
    20: "siddha",
    21: "sAdhya",
    22: "zubha",
    23: "zukla",
    24: "brahman",
    25: "aindra",
    26: "vaidhRti",
    27: "viSkambha",
}

KARANA_NAMES = {
    0: "kiMstughna",
    1: "bava",
    2: "bAlava",
    3: "kaulava",
    4: "taitila",
    5: "gara",
    6: "vaNij",
    7: "viSTi",
    8: "zakuni",
    9: "catuSpada",
    10: "nAga",
}

TITHI_LABELS_ML = {
    1: "പ്രതിപദ",
    2: "ദ്വിതീയ",
    3: "തൃതീയ",
    4: "ചതുര്ഥി",
    5: "പഞ്ചമി",
    6: "ഷഷ്ഠി",
    7: "സപ്തമി",
    8: "അഷ്ടമി",
    9: "നവമി",
    10: "ദശമി",
    11: "ഏകാദശി",
    12: "ദ്വാദശി",
    13: "ത്രയോദശി",
    14: "ചതുര്ദശി",
    15: "പൗർണ്ണമി/അമാവാസി",
}

# weekday(): Monday=0 ... Sunday=6
RAHU_SEGMENT = {0: 1, 1: 6, 2: 4, 3: 5, 4: 3, 5: 2, 6: 7}
GULIKA_SEGMENT = {0: 5, 1: 4, 2: 3, 3: 2, 4: 1, 5: 0, 6: 6}
YAMAGANDAM_SEGMENT = {0: 3, 1: 2, 2: 1, 3: 0, 4: 6, 5: 5, 6: 4}


@dataclass
class PanchangDay:
    event_date: date
    summary: str
    description: str


def trunc(value: float) -> int:
    return int(value)


def frac(value: float) -> float:
    return value - trunc(value)


def zero360(angle_degrees: float) -> float:
    result = angle_degrees % 360.0
    return 0.0 if result >= 360.0 else result


def modern_date_to_julian_day(year: int, month: int, day: int) -> float:
    if month < 3:
        year -= 1
        month += 12
    julian_day = trunc(365.25 * year) + trunc(30.59 * (month - 2)) + day + 1721086.5
    if year < 0:
        julian_day -= 1
        if (year % 4) == 0 and month >= 3:
            julian_day += 1
    if 2299160 < julian_day:
        julian_day += trunc(year / 400) - trunc(year / 100) + 2
    return julian_day


def julian_day_to_ahargana(julian_day: float) -> float:
    return julian_day - 588465.50


def ahargana_to_kali(ahargana: float) -> int:
    return trunc(ahargana * YUGA_ROTATION_SUN / YUGA_CIVIL_DAYS)


def kali_to_saka(kali_year: int) -> int:
    return kali_year - 3179


def saka_to_vikrama(saka_year: int) -> int:
    return saka_year + 135


def get_mean_long(ahargana: float, rotation: float) -> float:
    return 360 * frac(rotation * ahargana / YUGA_CIVIL_DAYS)


def arcsin(x: float) -> float:
    if EPS < abs(1 - x * x):
        return math.atan2(x / math.sqrt(1 - x * x), 1) * RAD
    if 0 < x:
        return 90
    return 270


def get_manda_equation(argument: float, planet: str) -> float:
    planet_circumm = {
        "sun": 13 + 50 / 60,
        "moon": 31 + 50 / 60,
        "mercury": 29,
        "venus": 11.5,
        "mars": 73.5,
        "jupiter": 32.5,
        "saturn": 48.5,
    }
    circumm = planet_circumm[planet]
    sin_term = circumm / 360 * math.sin(argument / RAD)
    if EPS < abs(1 - sin_term**2):
        return math.atan2(sin_term / math.sqrt(1 - sin_term**2), 1) * RAD
    return (PI / 2 * RAD) if sin_term > 0 else (3 * PI / 2 * RAD)


def get_true_solar_longitude(ahargana: float) -> float:
    mslong = get_mean_long(ahargana, YUGA_ROTATION_SUN)
    return zero360(mslong - get_manda_equation(mslong - SOLAR_APOGEE, "sun"))


def get_true_lunar_longitude(ahargana: float) -> float:
    mllong = get_mean_long(ahargana, YUGA_ROTATION_MOON)
    lunar_apogee = get_mean_long(ahargana, 488203) + 90
    return mllong - get_manda_equation(mllong - lunar_apogee, "moon")


def get_tithi(true_lunar_longitude: float, true_solar_longitude: float) -> float:
    elong = zero360(true_lunar_longitude - true_solar_longitude)
    return elong / 12


def get_tithi_set(tithi: float) -> tuple[int, float]:
    return trunc(tithi) + 1, frac(tithi)


def set_sukla_krsna(tithi_day: int) -> tuple[int, str]:
    if tithi_day > 15:
        return tithi_day - 15, "Krsna"
    return tithi_day, "Sukla"


def get_naksatra_name(true_lunar_longitude: float) -> str:
    idx = trunc(true_lunar_longitude * 27 / 360) % 28
    return NAKSHATRA_NAMES[idx]


def get_yoga_name(true_solar_longitude: float, true_lunar_longitude: float) -> str:
    yoga1 = zero360(true_solar_longitude + true_lunar_longitude)
    idx = trunc(yoga1 * 27 / 360) % 28
    return YOGA_NAMES[idx]


def get_karana_name(tithi: float) -> str:
    karana = trunc(2 * tithi)
    if karana == 0:
        return KARANA_NAMES[0]
    if karana < 57:
        karana = karana % 7
        return KARANA_NAMES[7] if karana == 0 else KARANA_NAMES[karana]
    if karana == 57:
        return KARANA_NAMES[8]
    if karana == 58:
        return KARANA_NAMES[9]
    if karana == 59:
        return KARANA_NAMES[10]
    return KARANA_NAMES[0]


def get_elong(ahargana: float) -> float:
    tllong = get_true_lunar_longitude(ahargana)
    tslong = get_true_solar_longitude(ahargana)
    elong = zero360(tllong - tslong)
    return 360 - elong if elong > 180 else elong


def three_relation(a: float, b: float, c: float) -> int:
    if (a < b) and (b < c):
        return 1
    if (c < b) and (b < a):
        return -1
    return 0


def find_conj(leftx: float, lefty: float, rightx: float, righty: float) -> float:
    width = (rightx - leftx) / 2
    centrex = (rightx + leftx) / 2
    if width < EPSIRON:
        return centrex

    centrey = get_elong(centrex)
    relation = three_relation(lefty, centrey, righty)
    if relation < 0:
        rightx = rightx + width
        righty = get_elong(rightx)
        return find_conj(centrex, centrey, rightx, righty)
    if relation > 0:
        leftx = leftx - width
        lefty = get_elong(leftx)
        return find_conj(leftx, lefty, centrex, centrey)

    leftx = leftx + width / 2
    lefty = get_elong(leftx)
    rightx = rightx - width / 2
    righty = get_elong(rightx)
    return find_conj(leftx, lefty, rightx, righty)


def get_conj(ahargana: float) -> float:
    conj_ahar = find_conj(ahargana - 2, get_elong(ahargana - 2), ahargana + 2, get_elong(ahargana + 2))
    return get_true_solar_longitude(conj_ahar)


def get_clong(ahargana: float, tithi: float) -> float:
    new_new = YUGA_CIVIL_DAYS / (YUGA_ROTATION_MOON - YUGA_ROTATION_SUN)
    ahar = ahargana - tithi * (new_new / 30)
    return get_conj(ahar)


def get_nclong(ahargana: float, tithi: float) -> float:
    new_new = YUGA_CIVIL_DAYS / (YUGA_ROTATION_MOON - YUGA_ROTATION_SUN)
    ahar = ahargana + (30 - tithi) * (new_new / 30)
    return get_conj(ahar)


def get_adhimasa(clong: float, nclong: float) -> str:
    return "Adhika-" if trunc(clong / 30) == trunc(nclong / 30) else ""


def get_masa_num(tslong: float, clong: float) -> int:
    masa_num = int(tslong / 30) % 12
    if (int(clong / 30) % 12) == masa_num:
        masa_num += 1
    return (masa_num + 12) % 12


def today_saura_masa_first_p(ahargana: float, desantara: float = 0.0) -> bool:
    tslong_today = get_true_solar_longitude(ahargana - desantara)
    tslong_tomorrow = get_true_solar_longitude(ahargana - desantara + 1)
    tslong_today -= int(tslong_today / 30) * 30
    tslong_tomorrow -= int(tslong_tomorrow / 30) * 30
    return (25 < tslong_today) and (tslong_tomorrow < 5)


def get_saura_masa_day(ahargana: float) -> tuple[int, int]:
    ahargana = trunc(ahargana)
    if today_saura_masa_first_p(ahargana):
        day = 1
        tslong_tomorrow = get_true_solar_longitude(ahargana + 1)
        month = trunc(tslong_tomorrow / 30) % 12
        return (month + 12) % 12, day
    month, day = get_saura_masa_day(ahargana - 1)
    return month, day + 1


def declination(longitude: float) -> float:
    return math.asin(math.sin(longitude / RAD) * math.sin(24.0 / RAD)) * RAD


def get_daylight_equation(year: int, loc_lat: float, ahargana: float) -> float:
    mslong = get_mean_long(ahargana, YUGA_ROTATION_SUN)
    samslong = mslong + (54 / 3600) * (year - 499)
    sdecl = declination(samslong)
    x = math.tan(loc_lat / RAD) * math.tan(sdecl / RAD)
    if EPS < abs(1 - x * x):
        return 0.5 * math.atan2(x / math.sqrt(1 - x * x), 1) / PI
    if x > 0:
        return 0.25
    return 0.75


def get_ayana_amsa(ahargana: float) -> tuple[int, int]:
    ay = (54 * YUGA_ROTATION_SUN / YUGA_CIVIL_DAYS / 3600) * (ahargana - 1314930)
    return trunc(ay), trunc(60 * frac(ay))


def fraction_to_minutes(day_fraction: float) -> int:
    return int(day_fraction * 24 * 60) % (24 * 60)


def format_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def format_period(start_min: float, end_min: float) -> str:
    return f"{format_hhmm(int(start_min))}-{format_hhmm(int(end_min))}"


def get_segment_window(sunrise_min: int, sunset_min: int, segment_index: int) -> str:
    day_span = sunset_min - sunrise_min
    if day_span <= 0:
        day_span += 24 * 60
    part = day_span / 8.0
    start = sunrise_min + segment_index * part
    end = start + part
    return format_period(start, end)


def kollavarsham_year(gregorian_year: int, saura_month_num: int) -> int:
    # Chingam (Simha=4) starts the Malayalam year.
    return gregorian_year - 824 if 4 <= saura_month_num <= 8 else gregorian_year - 825


def tithi_label_ml(tithi_day_15: int, paksha: str) -> str:
    if tithi_day_15 == 15:
        return "പൗർണ്ണമി" if paksha == "Sukla" else "അമാവാസി"
    return TITHI_LABELS_ML[tithi_day_15]


def paksha_label_ml(paksha: str) -> str:
    return "ശുക്ലപക്ഷം" if paksha == "Sukla" else "കൃഷ്ണപക്ഷം"


def compute_day_panchang(day_date: date, latitude: float, longitude: float) -> PanchangDay:
    jd = modern_date_to_julian_day(day_date.year, day_date.month, day_date.day)
    ahargana = julian_day_to_ahargana(jd)
    desantara = (longitude - UJJAIN_LONGITUDE) / 360.0
    ahargana_local = ahargana - desantara

    eqtime = get_daylight_equation(day_date.year, latitude, ahargana_local)
    sunrise_fraction = 0.25 - eqtime
    sunset_fraction = 0.75 + eqtime
    sunrise_min = fraction_to_minutes(sunrise_fraction)
    sunset_min = fraction_to_minutes(sunset_fraction)
    sunrise_str = format_hhmm(sunrise_min)
    sunset_str = format_hhmm(sunset_min)

    # Compute most Panchang elements at local sunrise.
    ahargana_sunrise = ahargana_local + sunrise_fraction
    tslong = get_true_solar_longitude(ahargana_sunrise)
    tllong = get_true_lunar_longitude(ahargana_sunrise)

    tithi = get_tithi(tllong, tslong)
    tithi_day, _ = get_tithi_set(tithi)
    tithi_day_15, paksha = set_sukla_krsna(tithi_day)
    tithi_ml = tithi_label_ml(tithi_day_15, paksha)

    nakshatra = get_naksatra_name(tllong)
    nakshatra_ml = NAKSHATRA_ML.get(nakshatra, nakshatra)
    yoga = get_yoga_name(tslong, tllong)
    karana = get_karana_name(tithi).strip()

    clong = get_clong(ahargana_sunrise, tithi)
    nclong = get_nclong(ahargana_sunrise, tithi)
    adhimasa = get_adhimasa(clong, nclong)
    masa_num = get_masa_num(tslong, clong)
    lunar_masa = LUNAR_MASA_NAMES[masa_num]
    lunar_masa_ml = LUNAR_MASA_ML[lunar_masa]
    if adhimasa:
        lunar_masa_ml = f"അധിക {lunar_masa_ml}"

    saura_month_num, saura_day = get_saura_masa_day(ahargana_local)
    saura_masa_sans = SAURA_MASA_NAMES[saura_month_num]
    mal_month_ml, mal_month_en = MALAYALAM_SOLAR_MONTHS[saura_month_num]
    kollavarsham = kollavarsham_year(day_date.year, saura_month_num)

    kali_year = ahargana_to_kali(ahargana_sunrise)
    saka_year = kali_to_saka(kali_year)
    vikrama_year = saka_to_vikrama(saka_year)
    ayana_deg, ayana_min = get_ayana_amsa(ahargana_sunrise)

    weekday_idx = day_date.weekday()
    weekday_ml = WEEKDAY_ML[weekday_idx]
    paksha_ml = paksha_label_ml(paksha)

    rahukalam = get_segment_window(sunrise_min, sunset_min, RAHU_SEGMENT[weekday_idx])
    gulikakalam = get_segment_window(sunrise_min, sunset_min, GULIKA_SEGMENT[weekday_idx])
    yamagandam = get_segment_window(sunrise_min, sunset_min, YAMAGANDAM_SEGMENT[weekday_idx])

    summary = f"{weekday_ml} • {mal_month_ml} {saura_day} • {paksha_ml} {tithi_ml}"

    desc_lines = [
        f"തീയതി: {day_date.isoformat()} ({weekday_ml})",
        f"മലയാളം തീയതി: കൊല്ലവർഷം {kollavarsham}, {mal_month_ml} {saura_day}",
        f"Malayalam Date: Kollavarsham {kollavarsham}, {mal_month_en} {saura_day}",
        f"തിഥി: {paksha_ml} {tithi_ml} (Tithi #{tithi_day})",
        f"നക്ഷത്രം: {nakshatra_ml} ({nakshatra})",
        f"യോഗം: {yoga}",
        f"കരണം: {karana}",
        f"ചന്ദ്രമാസം: {lunar_masa_ml} ({lunar_masa})",
        f"സൗരമാസം: {mal_month_ml} ({saura_masa_sans})",
        f"സൂര്യോദയം: {sunrise_str}",
        f"സൂര്യാസ്തമയം: {sunset_str}",
        f"രാഹുകാലം: {rahukalam}",
        f"ഗുളികകാലം: {gulikakalam}",
        f"യമഗണ്ഡം: {yamagandam}",
        f"Ayanamsa: {ayana_deg}° {ayana_min}'",
        f"Era Years: Saka {saka_year}, Vikrama {vikrama_year}, Kali {kali_year}",
        "ഗണനാ രീതി: സൂര്യസിദ്ധാന്തത്തെ അടിസ്ഥാനമാക്കിയ പഞ്ചാംഗ കണക്കുകൂട്ടൽ",
    ]

    description = "\n".join(desc_lines)
    return PanchangDay(event_date=day_date, summary=summary, description=description)


def escape_ics_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", r"\n")
    )


def fold_ics_line(line: str, limit: int = 75) -> list[str]:
    if len(line.encode("utf-8")) <= limit:
        return [line]

    parts: list[str] = []
    chunk: list[str] = []
    chunk_bytes = 0
    current_limit = limit

    for ch in line:
        b = ch.encode("utf-8")
        if chunk and (chunk_bytes + len(b) > current_limit):
            parts.append("".join(chunk))
            chunk = [ch]
            chunk_bytes = len(b)
            current_limit = limit - 1
        else:
            chunk.append(ch)
            chunk_bytes += len(b)

    if chunk:
        parts.append("".join(chunk))

    return [parts[0]] + [f" {p}" for p in parts[1:]]


def build_ics(
    entries: list[PanchangDay],
    calendar_name: str,
    timezone_name: str,
    location_name: str,
    source_note: str,
) -> str:
    now_utc = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    cal_uid = str(uuid.uuid4())

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "PRODID:-//Malayalam Panchangam Generator//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(calendar_name)}",
        f"X-WR-TIMEZONE:{escape_ics_text(timezone_name)}",
        f"X-WR-CALDESC:{escape_ics_text(source_note)}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]

    for item in entries:
        dtstart = item.event_date.strftime("%Y%m%d")
        dtend = (item.event_date + timedelta(days=1)).strftime("%Y%m%d")
        uid = f"{dtstart}-{location_name.lower().replace(' ', '-')}-{cal_uid}@malayalam-panchangam"

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_utc}",
                f"DTSTART;VALUE=DATE:{dtstart}",
                f"DTEND;VALUE=DATE:{dtend}",
                f"SUMMARY:{escape_ics_text(item.summary)}",
                f"DESCRIPTION:{escape_ics_text(item.description)}",
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")

    folded: list[str] = []
    for line in lines:
        folded.extend(fold_ics_line(line))
    return "\r\n".join(folded) + "\r\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Malayalam Panchangam calendar (.ics) for Google Calendar subscription."
    )
    parser.add_argument("--start", help="Start date (YYYY-MM-DD). Ignored if --year is used.")
    parser.add_argument("--end", help="End date inclusive (YYYY-MM-DD). Ignored if --year is used.")
    parser.add_argument("--days", type=int, default=730, help="Number of days from start date if --end is not provided.")
    parser.add_argument("--year", type=int, help="Generate full Gregorian year (Jan 1 to Dec 31).")
    parser.add_argument("--latitude", type=float, default=8.5241, help="Location latitude.")
    parser.add_argument("--longitude", type=float, default=76.9366, help="Location longitude.")
    parser.add_argument("--timezone", default="Asia/Kolkata", help="Calendar timezone metadata.")
    parser.add_argument("--location-name", default="Thiruvananthapuram", help="Location name for UID/source.")
    parser.add_argument("--calendar-name", default="Malayalam Panchangam", help="Calendar name.")
    parser.add_argument("--output", default="public/malayalam-panchangam.ics", help="Output .ics path.")
    return parser.parse_args()


def resolve_range(args: argparse.Namespace) -> tuple[date, date]:
    if args.year:
        return date(args.year, 1, 1), date(args.year, 12, 31)

    if args.start:
        start = date.fromisoformat(args.start)
    else:
        start = date.today()

    if args.end:
        end = date.fromisoformat(args.end)
    else:
        end = start + timedelta(days=max(args.days - 1, 0))

    if end < start:
        raise ValueError("--end must be on or after --start")
    return start, end


def main() -> None:
    args = parse_args()
    start_date, end_date = resolve_range(args)

    entries: list[PanchangDay] = []
    current = start_date
    while current <= end_date:
        entries.append(compute_day_panchang(current, args.latitude, args.longitude))
        current += timedelta(days=1)

    source_note = (
        f"Daily Malayalam Panchangam for {args.location_name} "
        f"(lat={args.latitude}, lon={args.longitude})"
    )
    ics_text = build_ics(
        entries=entries,
        calendar_name=args.calendar_name,
        timezone_name=args.timezone,
        location_name=args.location_name,
        source_note=source_note,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ics_text, encoding="utf-8", newline="")
    print(f"Wrote {len(entries)} events to {output_path}")


if __name__ == "__main__":
    main()

