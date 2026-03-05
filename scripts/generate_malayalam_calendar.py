#!/usr/bin/env python3
"""Generate a multi-event Malayalam Panchangam ICS feed.

This version creates separate events for date, nakshatra windows, rahukalam,
sunrise/sunset, special observances, summary, and a daily spiritual quote.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import panchang_core as core


DAILY_QUOTES = [
    ("കർമം ചെയ്യാനുള്ള അവകാശം നിനക്കുണ്ട്; ഫലത്തിൽ ആസക്തിയില്ലാതെ പ്രവർത്തിക്കൂ.", "ഭഗവദ്ഗീത 2.47 (സാരം)"),
    ("മനം കീഴടക്കുന്നവനാണ് യഥാർത്ഥ സുഹൃത്തും ജയിയും.", "ഭഗവദ്ഗീത 6.6 (സാരം)"),
    ("ധർമ്മം കാത്താൽ ധർമ്മം നമ്മെ കാക്കും.", "സനാതന ധർമ്മസാരം"),
    ("സമത്വബുദ്ധിയാണ് യോഗം.", "ഭഗവദ്ഗീത 2.48 (സാരം)"),
    ("അഹങ്കാരം കുറയുമ്പോൾ ഉള്ളിലെ പ്രകാശം തെളിയും.", "ഉപനിഷദ് സാരം"),
    ("ഒരു ജാതി, ഒരു മതം, ഒരു ദൈവം മനുഷ്യന്.", "ശ്രീ നാരായണ ഗുരു"),
    ("ഉണരുക, എഴുന്നേൽക്കുക, ലക്ഷ്യം കൈവരിക്കുന്നതുവരെ നിർത്തരുത്.", "സ്വാമി വിവേകാനന്ദൻ"),
    ("നന്മ ചെയ്താൽ നന്മ തന്നെ തിരിച്ചെത്തും.", "ധാർമ്മിക ചിന്ത"),
    ("ഭയം വിട്ടാൽ ഭക്തി ആഴം നേടും.", "ആത്മീയ സാരം"),
    ("സത്യം ശാന്തിയിൽ വളരുന്നു.", "വേദാന്ത ചിന്ത"),
    ("ക്രോധം ബുദ്ധിയെ മറയ്ക്കും; ക്ഷമ ബുദ്ധിയെ തെളിയിക്കും.", "ഗീതാ സാരം"),
    ("സ്വയം അറിയുക എന്നതാണ് ജ്ഞാനത്തിന്റെ തുടക്കം.", "ഉപനിഷദ് സാരം"),
    ("പരോപകാരം തന്നെയാണ് പരമ പൂജ.", "ഭക്തി പാരമ്പര്യം"),
    ("എല്ലാ ജീവജാലങ്ങളിലും ദൈവദർശനം നേടുക.", "വേദാന്ത സാരം"),
    ("ഭക്തിയിൽ സ്ഥിരത ഉണ്ടെങ്കിൽ മനസിന് ശാന്തി ലഭിക്കും.", "ഭക്തി ചിന്ത"),
    ("ധൈര്യവും ധർമ്മവും കൂടെ നിൽക്കുമ്പോൾ വഴി തുറക്കും.", "ആത്മീയ സന്ദേശം"),
    ("അകത്തെ നിശ്ശബ്ദതയിൽ ആത്മാവ് സംസാരിക്കുന്നു.", "ധ്യാന സാരം"),
    ("സ്നേഹം തന്നെയാണ് ആത്മീയതയുടെ ലളിതമായ വഴി.", "സാന്ത്വന ചിന്ത"),
    ("സ്വാർത്ഥത കുറയുമ്പോൾ ദൈവാനുഭവം വർധിക്കും.", "സനാതന സാരം"),
    ("പ്രാർത്ഥന ഹൃദയത്തെ ശുദ്ധമാക്കുന്ന നിശ്ശബ്ദ ശക്തിയാണ്.", "ആത്മീയ മാർഗ്ഗദർശനം"),
]


@dataclass
class CalendarEvent:
    uid_seed: str
    summary: str
    description: str
    all_day: bool
    start_date: date
    end_date: date | None = None
    start_minute: int | None = None
    end_minute: int | None = None
    transparent: bool = True


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug if slug else "location"


def format_hhmm_local(minutes: int) -> str:
    return core.format_hhmm(minutes % (24 * 60))


def format_period(start_minute: int, end_minute: int, keep_24_end: bool = False) -> str:
    start_label = format_hhmm_local(start_minute)
    if keep_24_end and end_minute == 24 * 60:
        end_label = "24:00"
    else:
        end_label = format_hhmm_local(end_minute)
    return f"{start_label}-{end_label}"


def get_segment_bounds(sunrise_min: int, sunset_min: int, segment_index: int) -> tuple[int, int]:
    day_span = sunset_min - sunrise_min
    if day_span <= 0:
        day_span += 24 * 60
    part = day_span / 8.0
    start = int(round(sunrise_min + segment_index * part))
    end = int(round(sunrise_min + (segment_index + 1) * part))
    return start, end


def minute_to_date_time(base_date: date, minute: int) -> tuple[date, int, int]:
    day_offset, minute_in_day = divmod(minute, 24 * 60)
    date_value = base_date + timedelta(days=day_offset)
    hour = minute_in_day // 60
    minute_part = minute_in_day % 60
    return date_value, hour, minute_part


def get_quote_for_day(day_date: date) -> tuple[str, str]:
    return DAILY_QUOTES[day_date.toordinal() % len(DAILY_QUOTES)]


def make_all_day_event(uid_seed: str, day_date: date, summary: str, description: str) -> CalendarEvent:
    return CalendarEvent(
        uid_seed=uid_seed,
        summary=summary,
        description=description,
        all_day=True,
        start_date=day_date,
    )


def make_timed_event(
    uid_seed: str,
    day_date: date,
    summary: str,
    description: str,
    start_minute: int,
    end_minute: int,
) -> CalendarEvent:
    if end_minute <= start_minute:
        end_minute += 24 * 60

    return CalendarEvent(
        uid_seed=uid_seed,
        summary=summary,
        description=description,
        all_day=False,
        start_date=day_date,
        start_minute=start_minute,
        end_minute=end_minute,
    )


def build_day_events(day_date: date, latitude: float, longitude: float) -> list[CalendarEvent]:
    jd = core.modern_date_to_julian_day(day_date.year, day_date.month, day_date.day)
    ahargana = core.julian_day_to_ahargana(jd)
    desantara = (longitude - core.UJJAIN_LONGITUDE) / 360.0
    ahargana_local = ahargana - desantara

    eqtime = core.get_daylight_equation(day_date.year, latitude, ahargana_local)
    sunrise_fraction = 0.25 - eqtime
    sunset_fraction = 0.75 + eqtime
    sunrise_min = core.fraction_to_minutes(sunrise_fraction)
    sunset_min = core.fraction_to_minutes(sunset_fraction)
    sunrise_str = core.format_hhmm(sunrise_min)
    sunset_str = core.format_hhmm(sunset_min)

    ahargana_sunrise = ahargana_local + sunrise_fraction
    tslong = core.get_true_solar_longitude(ahargana_sunrise)
    tllong = core.get_true_lunar_longitude(ahargana_sunrise)

    tithi = core.get_tithi(tllong, tslong)
    tithi_day, _ = core.get_tithi_set(tithi)
    tithi_day_15, paksha = core.set_sukla_krsna(tithi_day)
    tithi_ml = core.tithi_label_ml(tithi_day_15, paksha)
    paksha_ml = core.paksha_label_ml(paksha)

    nakshatra = core.get_naksatra_name(tllong)
    nakshatra_ml = core.NAKSHATRA_ML.get(nakshatra, nakshatra)
    naksatra_segments = core.get_naksatra_segments_for_day(ahargana_local)

    yoga = core.get_yoga_name(tslong, tllong)
    karana = core.get_karana_name(tithi).strip()

    clong = core.get_clong(ahargana_sunrise, tithi)
    nclong = core.get_nclong(ahargana_sunrise, tithi)
    adhimasa = core.get_adhimasa(clong, nclong)
    masa_num = core.get_masa_num(tslong, clong)
    lunar_masa = core.LUNAR_MASA_NAMES[masa_num]
    lunar_masa_ml = core.LUNAR_MASA_ML[lunar_masa]
    if adhimasa:
        lunar_masa_ml = f"അധിക {lunar_masa_ml}"

    saura_month_num, saura_day = core.get_saura_masa_day(ahargana_local)
    saura_masa_sans = core.SAURA_MASA_NAMES[saura_month_num]
    mal_month_ml, mal_month_en = core.MALAYALAM_SOLAR_MONTHS[saura_month_num]
    kollavarsham = core.kollavarsham_year(day_date.year, saura_month_num)

    kali_year = core.ahargana_to_kali(ahargana_sunrise)
    saka_year = core.kali_to_saka(kali_year)
    vikrama_year = core.saka_to_vikrama(saka_year)
    ayana_deg, ayana_min = core.get_ayana_amsa(ahargana_sunrise)

    weekday_idx = day_date.weekday()
    weekday_ml = core.WEEKDAY_ML[weekday_idx]

    rahu_start, rahu_end = get_segment_bounds(sunrise_min, sunset_min, core.RAHU_SEGMENT[weekday_idx])
    gulika_start, gulika_end = get_segment_bounds(sunrise_min, sunset_min, core.GULIKA_SEGMENT[weekday_idx])
    yama_start, yama_end = get_segment_bounds(sunrise_min, sunset_min, core.YAMAGANDAM_SEGMENT[weekday_idx])

    rahukalam = format_period(rahu_start, rahu_end)
    gulikakalam = format_period(gulika_start, gulika_end)
    yamagandam = format_period(yama_start, yama_end)

    quote_text, quote_source = get_quote_for_day(day_date)

    nakshatra_timeline_parts: list[str] = []
    for seg_start, seg_end, seg_idx in naksatra_segments:
        seg_name = core.NAKSHATRA_NAMES[seg_idx]
        seg_ml = core.NAKSHATRA_ML.get(seg_name, seg_name)
        nakshatra_timeline_parts.append(f"{seg_ml} ({seg_name}) {format_period(seg_start, seg_end, keep_24_end=True)}")

    events: list[CalendarEvent] = []

    # 1) Date event
    events.append(
        make_all_day_event(
            uid_seed="date",
            day_date=day_date,
            summary=f"🗓️ മലയാളം തീയതി: {mal_month_ml} {saura_day}",
            description=(
                f"📅 {day_date.isoformat()} ({weekday_ml})\n"
                f"🗓️ കൊല്ലവർഷം {kollavarsham}, {mal_month_ml} {saura_day}\n"
                f"🌞 സൗരമാസം: {mal_month_ml} ({saura_masa_sans})\n"
                f"📖 Malayalam Date: Kollavarsham {kollavarsham}, {mal_month_en} {saura_day}"
            ),
        )
    )

    # 2) Nakshatra event(s)
    if len(naksatra_segments) == 1:
        only_start, only_end, only_idx = naksatra_segments[0]
        only_name = core.NAKSHATRA_NAMES[only_idx]
        only_ml = core.NAKSHATRA_ML.get(only_name, only_name)
        events.append(
            make_all_day_event(
                uid_seed="nakshatra-full",
                day_date=day_date,
                summary=f"🌟 നക്ഷത്രം: {only_ml}",
                description=(
                    f"🌟 ഇന്നത്തെ നക്ഷത്രം: {only_ml} ({only_name})\n"
                    f"🕒 സമയം: {format_period(only_start, only_end, keep_24_end=True)}"
                ),
            )
        )
    else:
        for index, (seg_start, seg_end, seg_idx) in enumerate(naksatra_segments, start=1):
            seg_name = core.NAKSHATRA_NAMES[seg_idx]
            seg_ml = core.NAKSHATRA_ML.get(seg_name, seg_name)
            events.append(
                make_timed_event(
                    uid_seed=f"nakshatra-{index}",
                    day_date=day_date,
                    summary=f"🌟 നക്ഷത്രം: {seg_ml}",
                    description=(
                        f"🌟 {seg_ml} ({seg_name})\n"
                        f"🕒 {format_period(seg_start, seg_end, keep_24_end=True)}"
                    ),
                    start_minute=seg_start,
                    end_minute=seg_end,
                )
            )

    # 3) Rahukalam
    events.append(
        make_timed_event(
            uid_seed="rahukalam",
            day_date=day_date,
            summary="⚠️ രാഹുകാലം",
            description=(
                f"⚠️ രാഹുകാലം: {rahukalam}\n"
                "ഈ സമയം പ്രധാന ശുഭാരംഭങ്ങൾ ഒഴിവാക്കുന്നത് പതിവാണ്."
            ),
            start_minute=rahu_start,
            end_minute=rahu_end,
        )
    )

    # 4) Sunrise/Sunset events
    events.append(
        make_timed_event(
            uid_seed="sunrise",
            day_date=day_date,
            summary="🌅 സൂര്യോദയം",
            description=f"🌅 സൂര്യോദയം: {sunrise_str}",
            start_minute=sunrise_min,
            end_minute=sunrise_min + 10,
        )
    )
    events.append(
        make_timed_event(
            uid_seed="sunset",
            day_date=day_date,
            summary="🌇 സൂര്യാസ്തമയം",
            description=f"🌇 സൂര്യാസ്തമയം: {sunset_str}",
            start_minute=sunset_min,
            end_minute=sunset_min + 10,
        )
    )

    # 5) Special observances
    if tithi_day_15 == 11:
        events.append(
            make_all_day_event(
                uid_seed="ekadashi",
                day_date=day_date,
                summary="🙏 ഏകാദശി",
                description=f"🙏 ഇന്ന് ഏകാദശി ({paksha_ml}).\n🌙 തിഥി: {paksha_ml} {tithi_ml}",
            )
        )

    if tithi_day_15 == 13:
        events.append(
            make_timed_event(
                uid_seed="pradosham",
                day_date=day_date,
                summary="🕯️ പ്രദോഷകാലം",
                description=(
                    f"🕯️ ഇന്ന് പ്രദോഷം ({paksha_ml}).\n"
                    f"🕒 ഏകദേശം: {format_period(sunset_min - 90, sunset_min + 90)}"
                ),
                start_minute=sunset_min - 90,
                end_minute=sunset_min + 90,
            )
        )

    if tithi_day_15 == 15 and paksha == "Sukla":
        events.append(
            make_all_day_event(
                uid_seed="purnima",
                day_date=day_date,
                summary="🌕 പൗർണ്ണമി",
                description="🌕 ഇന്ന് പൗർണ്ണമി (പൂർണ്ണചന്ദ്ര ദിനം).",
            )
        )

    if tithi_day_15 == 15 and paksha == "Krsna":
        events.append(
            make_all_day_event(
                uid_seed="amavasya",
                day_date=day_date,
                summary="🌑 അമാവാസി",
                description="🌑 ഇന്ന് അമാവാസി (നിലാവില്ലാ ദിനം).",
            )
        )

    # 6) Pretty summary event
    events.append(
        make_all_day_event(
            uid_seed="summary",
            day_date=day_date,
            summary=f"📿 പഞ്ചാംഗ സാരാംശം • {weekday_ml}",
            description=(
                f"📅 തീയതി: {day_date.isoformat()} ({weekday_ml})\n"
                f"🌙 തിഥി: {paksha_ml} {tithi_ml} (#{tithi_day})\n"
                f"🌟 നക്ഷത്രം (സൂര്യോദയത്തിൽ): {nakshatra_ml} ({nakshatra})\n"
                f"🌠 നക്ഷത്രക്രമം: {'; '.join(nakshatra_timeline_parts)}\n"
                f"🧘 യോഗം: {yoga}\n"
                f"🪔 കരണം: {karana}\n"
                f"🌔 ചന്ദ്രമാസം: {lunar_masa_ml} ({lunar_masa})\n"
                f"🌞 സൗരമാസം: {mal_month_ml} ({saura_masa_sans})\n"
                f"🌅 സൂര്യോദയം: {sunrise_str}\n"
                f"🌇 സൂര്യാസ്തമയം: {sunset_str}\n"
                f"⚫ രാഹുകാലം: {rahukalam}\n"
                f"🟤 ഗുളികകാലം: {gulikakalam}\n"
                f"🔵 യമഗണ്ഡം: {yamagandam}\n"
                f"🧭 അയ്യനാംശം: {ayana_deg}° {ayana_min}'\n"
                f"📚 Era Years: Saka {saka_year}, Vikrama {vikrama_year}, Kali {kali_year}"
            ),
        )
    )

    # 7) Daily quote event
    events.append(
        make_all_day_event(
            uid_seed="quote",
            day_date=day_date,
            summary="🕉️ ഇന്നത്തെ ആത്മീയചിന്ത",
            description=f"“{quote_text}”\n— {quote_source}",
        )
    )

    return events


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
    events: list[CalendarEvent],
    calendar_name: str,
    timezone_name: str,
    location_name: str,
    source_note: str,
) -> str:
    now_utc = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    location_slug = slugify(location_name)

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

    for event in events:
        date_token = event.start_date.strftime("%Y%m%d")
        uid = f"{date_token}-{location_slug}-{event.uid_seed}@malayalam-panchangam"
        transparency = "TRANSPARENT" if event.transparent else "OPAQUE"

        lines.extend(["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{now_utc}"])

        if event.all_day:
            dtstart = event.start_date.strftime("%Y%m%d")
            dtend_date = event.end_date if event.end_date else event.start_date + timedelta(days=1)
            dtend = dtend_date.strftime("%Y%m%d")
            lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
            lines.append(f"DTEND;VALUE=DATE:{dtend}")
        else:
            if event.start_minute is None or event.end_minute is None:
                raise ValueError("Timed event is missing start_minute/end_minute")

            s_date, s_hour, s_min = minute_to_date_time(event.start_date, event.start_minute)
            e_date, e_hour, e_min = minute_to_date_time(event.start_date, event.end_minute)
            dtstart = f"{s_date.strftime('%Y%m%d')}T{s_hour:02d}{s_min:02d}00"
            dtend = f"{e_date.strftime('%Y%m%d')}T{e_hour:02d}{e_min:02d}00"

            lines.append(f"DTSTART;TZID={escape_ics_text(timezone_name)}:{dtstart}")
            lines.append(f"DTEND;TZID={escape_ics_text(timezone_name)}:{dtend}")

        lines.extend(
            [
                f"SUMMARY:{escape_ics_text(event.summary)}",
                f"DESCRIPTION:{escape_ics_text(event.description)}",
                f"TRANSP:{transparency}",
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

    events: list[CalendarEvent] = []
    current = start_date
    while current <= end_date:
        events.extend(build_day_events(current, args.latitude, args.longitude))
        current += timedelta(days=1)

    source_note = (
        f"Daily Malayalam Panchangam for {args.location_name} "
        f"(lat={args.latitude}, lon={args.longitude})"
    )

    ics_text = build_ics(
        events=events,
        calendar_name=args.calendar_name,
        timezone_name=args.timezone,
        location_name=args.location_name,
        source_note=source_note,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ics_text, encoding="utf-8", newline="")
    print(f"Wrote {len(events)} events to {output_path}")


if __name__ == "__main__":
    main()
