import os
import time
import json
import requests
import pandas as pd

from datetime import datetime, timedelta
from pathlib import Path

from dhanhq import DhanContext, dhanhq


# ============================================================
# DHAN SETTINGS
# ============================================================

CLIENT_ID = "1102566905"

# IMPORTANT:
# API token ko code mein hard-code MAT karo.
#
# Windows CMD:
# set DHAN_ACCESS_TOKEN=YOUR_NEW_TOKEN
#
# PowerShell:
# $env:DHAN_ACCESS_TOKEN="YOUR_NEW_TOKEN"
#
# Agar environment variable nahi mila,
# program token manually maangega.
# ============================================================

ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

if not ACCESS_TOKEN:

    ACCESS_TOKEN = input(
        "Enter NEW Dhan Access Token: "
    ).strip()


if not ACCESS_TOKEN:

    raise Exception(
        "Dhan Access Token nahi mila."
    )


print(
    "Token found: True"
)


# ============================================================
# DHAN CONNECTION
# ============================================================

context = DhanContext(
    CLIENT_ID,
    ACCESS_TOKEN
)

dhan = dhanhq(
    context
)

print(
    "Dhan connection created ✅"
)


# ============================================================
# SETTINGS
# ============================================================

INDEX = "NIFTY"

SECURITY_ID = 13

UNDERLYING_SEGMENT = "IDX_I"

OPTION_SEGMENT = "NSE_FNO"

ATM_RANGE = 5

# ============================================================
# OPTION PREMIUM TRADE PLAN
# ============================================================
# Entry = current selected option premium + 2% trigger buffer.
# SL    = selected option's PREVIOUS CLOSE from option chain.
# T1    = Entry + 2R.
# T2    = Entry + 3R.
# Therefore SL/Targets are anchored to actual option-chain data
# instead of fixed percentage SL/Target values.
# Values are rounded to the 0.05 option tick.
# ============================================================

ENTRY_BUFFER_PCT = 0.02



# ============================================================
# LOCAL SNAPSHOT FILE
# ============================================================

SNAPSHOT_FILE = Path(
    "trade_burner_option_snapshot.json"
)


# ============================================================
# HEADER
# ============================================================

print(
    "\n=========================================="
)

print(
    "TRADE BURNER OPTION CHAIN ANALYZER"
)

print(
    "=========================================="
)

print(
    f"Index            : {INDEX}"
)

print(
    f"Security ID      : {SECURITY_ID}"
)

print(
    f"Underlying Seg.  : {UNDERLYING_SEGMENT}"
)

print(
    f"ATM Range        : ±{ATM_RANGE} strikes"
)
print(
    "Analysis Mode    : PURE OPTION CHAIN"
)



# ============================================================
# DIRECT DHAN API HEADERS
# ============================================================

HEADERS = {

    "Content-Type":
        "application/json",

    "access-token":
        ACCESS_TOKEN,

    "client-id":
        CLIENT_ID

}


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value):

    if value is None:

        return 0.0

    try:

        return float(value)

    except Exception:

        return 0.0


# ============================================================
# LOAD PREVIOUS SNAPSHOT
# ============================================================

def load_previous_snapshot():

    if not SNAPSHOT_FILE.exists():

        return {}

    try:

        with open(
            SNAPSHOT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if isinstance(
            data,
            dict
        ):

            return data

    except Exception as e:

        print(
            "\n⚠️ Previous snapshot read error:",
            e
        )

    return {}


# ============================================================
# SAVE CURRENT SNAPSHOT
# ============================================================

def save_current_snapshot(
    snapshot
):

    try:

        with open(
            SNAPSHOT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                snapshot,
                file,
                indent=2
            )

        print(
            "\n✅ OI snapshot saved."
        )

    except Exception as e:

        print(
            "\n⚠️ Snapshot save error:",
            e
        )


# ============================================================
# GET OI CHANGE
# ============================================================

def get_oi_change(
    option_data,
    previous_snapshot,
    strike,
    option_type
):

    # --------------------------------------------------------
    # METHOD 1
    # Direct oi_change field
    # --------------------------------------------------------

    direct_change = option_data.get(
        "oi_change"
    )

    if direct_change is not None:

        return (
            safe_float(
                direct_change
            ),
            "API"
        )


    # --------------------------------------------------------
    # METHOD 2
    # previous_oi field
    # --------------------------------------------------------

    current_oi = safe_float(
        option_data.get(
            "oi"
        )
    )

    previous_oi = option_data.get(
        "previous_oi"
    )

    if previous_oi is not None:

        previous_oi = safe_float(
            previous_oi
        )

        return (
            current_oi - previous_oi,
            "PREVIOUS_OI"
        )


    # --------------------------------------------------------
    # METHOD 3
    # LOCAL SNAPSHOT
    # --------------------------------------------------------

    strike_key = str(
        int(strike)
    )

    previous_strike = (
        previous_snapshot
        .get(
            strike_key,
            {}
        )
    )

    previous_oi_local = safe_float(
        previous_strike.get(
            option_type,
            0
        )
    )

    if previous_oi_local > 0:

        return (
            current_oi -
            previous_oi_local,
            "SNAPSHOT"
        )


    # --------------------------------------------------------
    # METHOD 4
    # NO BASELINE
    # --------------------------------------------------------

    return (
        0.0,
        "NO_BASELINE"
    )


# ============================================================
# GET EXPIRIES
# ============================================================

def get_expiries():

    print(
        "\n=========================================="
    )

    print(
        "GETTING EXPIRIES"
    )

    print(
        "=========================================="
    )

    url = (
        "https://api.dhan.co/v2/"
        "optionchain/expirylist"
    )

    payload = {

        "UnderlyingScrip":
            SECURITY_ID,

        "UnderlyingSeg":
            UNDERLYING_SEGMENT

    }


    for attempt in range(
        1,
        4
    ):

        print(
            f"\nExpiry API attempt "
            f"{attempt}/3..."
        )

        try:

            response = requests.post(

                url,

                headers=HEADERS,

                json=payload,

                timeout=15

            )

            print(
                "HTTP Status:",
                response.status_code
            )


            try:

                result = response.json()

            except Exception:

                print(
                    "❌ Invalid JSON response:"
                )

                print(
                    response.text
                )

                result = None


            if (

                isinstance(
                    result,
                    dict
                )

                and

                result.get(
                    "status"
                )
                ==
                "success"

            ):

                expiries = result.get(
                    "data"
                )


                if (

                    isinstance(
                        expiries,
                        list
                    )

                    and

                    expiries

                ):

                    print(
                        f"\n✅ Received "
                        f"{len(expiries)} "
                        f"expiry dates."
                    )

                    return expiries


            print(
                "\n⚠️ Expiry API failed."
            )


        except Exception as e:

            print(
                "\n❌ Expiry request error:",
                e
            )


        if attempt < 3:

            time.sleep(
                3
            )


    return []


# ============================================================
# GET OPTION CHAIN
# ============================================================

def get_option_chain(
    expiry
):

    print(
        "\n=========================================="
    )

    print(
        "GETTING OPTION CHAIN"
    )

    print(
        "=========================================="
    )

    print(
        "Expiry:",
        expiry
    )


    url = (
        "https://api.dhan.co/v2/"
        "optionchain"
    )


    payload = {

        "UnderlyingScrip":
            SECURITY_ID,

        "UnderlyingSeg":
            UNDERLYING_SEGMENT,

        "Expiry":
            expiry

    }


    print(
        "\nRequest Body:"
    )

    print(
        payload
    )


    # Dhan API rate-limit protection
    time.sleep(
        3
    )


    for attempt in range(
        1,
        4
    ):

        print(
            f"\nOption Chain attempt "
            f"{attempt}/3..."
        )


        try:

            response = requests.post(

                url,

                headers=HEADERS,

                json=payload,

                timeout=20

            )


            print(
                "HTTP Status:",
                response.status_code
            )


            try:

                result = response.json()

            except Exception:

                print(
                    "\n❌ Invalid JSON:"
                )

                print(
                    response.text
                )

                result = None


            if (

                isinstance(
                    result,
                    dict
                )

                and

                result.get(
                    "status"
                )
                ==
                "success"

            ):

                print(
                    "\n✅ OPTION CHAIN "
                    "RECEIVED!"
                )

                return result


            print(
                "\n⚠️ Option Chain API failed:"
            )

            print(
                result
            )


        except Exception as e:

            print(
                "\n❌ Option Chain request error:",
                e
            )


        if attempt < 3:

            print(
                "Waiting 4 seconds "
                "before retry..."
            )

            time.sleep(
                4
            )


    return None


# ============================================================
# PARSE OPTION CHAIN
# ============================================================

def parse_option_chain(
    response,
    expiry
):

    print(
        "\n=========================================="
    )

    print(
        "PARSING OPTION CHAIN"
    )

    print(
        "=========================================="
    )


    if not isinstance(
        response,
        dict
    ):

        print(
            "❌ Invalid response."
        )

        return None


    print(
        "Top-level keys:",
        list(
            response.keys()
        )
    )


    data = response.get(
        "data"
    )


    if not isinstance(
        data,
        dict
    ):

        print(
            "❌ 'data' missing."
        )

        return None


    print(
        "Inner keys:",
        list(
            data.keys()
        )
    )


    oc = data.get(
        "oc"
    )


    if not isinstance(
        oc,
        dict
    ):

        print(
            "❌ 'oc' missing."
        )

        return None


    spot = safe_float(
        data.get(
            "last_price"
        )
    )


    if spot <= 0:

        print(
            "❌ Spot price missing."
        )

        return None


    # ========================================================
    # PREVIOUS SNAPSHOT
    # ========================================================

    previous_snapshot = (
        load_previous_snapshot()
    )


    rows = []

    current_snapshot = {}


    # ========================================================
    # STRIKE-WISE DATA
    # ========================================================

    for strike_key, item in oc.items():

        try:

            strike = float(
                strike_key
            )

        except Exception:

            continue


        if not isinstance(
            item,
            dict
        ):

            continue


        ce = (
            item.get(
                "ce"
            )
            or {}
        )


        pe = (
            item.get(
                "pe"
            )
            or {}
        )


        # ====================================================
        # DEBUG FIRST STRIKE
        # ====================================================

        if not rows:

            print(
                "\n=========================================="
            )

            print(
                "OPTION DATA FIELD CHECK"
            )

            print(
                "=========================================="
            )

            print(
                "CE fields:",
                list(
                    ce.keys()
                )
            )

            print(
                "PE fields:",
                list(
                    pe.keys()
                )
            )


        # ====================================================
        # CE OI CHANGE
        # ====================================================

        ce_change_oi, ce_change_method = (
            get_oi_change(
                ce,
                previous_snapshot,
                strike,
                "CE"
            )
        )


        # ====================================================
        # PE OI CHANGE
        # ====================================================

        pe_change_oi, pe_change_method = (
            get_oi_change(
                pe,
                previous_snapshot,
                strike,
                "PE"
            )
        )


        current_ce_oi = safe_float(
            ce.get(
                "oi"
            )
        )


        current_pe_oi = safe_float(
            pe.get(
                "oi"
            )
        )


        # ====================================================
        # SAVE SNAPSHOT DATA
        # ====================================================

        strike_key_clean = str(
            int(strike)
        )


        current_snapshot[
            strike_key_clean
        ] = {

            "CE":
                current_ce_oi,

            "PE":
                current_pe_oi

        }


        rows.append({

            "strike":
                strike,

            "CE_LTP":
                safe_float(
                    ce.get(
                        "last_price"
                    )
                ),

            "CE_PreviousClose":
                safe_float(
                    ce.get(
                        "previous_close_price"
                    )
                ),

            "CE_OI":
                current_ce_oi,

            "CE_ChangeOI":
                ce_change_oi,

            "CE_ChangeMethod":
                ce_change_method,

            "CE_Volume":
                safe_float(
                    ce.get(
                        "volume"
                    )
                ),

            "CE_IV":
                safe_float(
                    ce.get(
                        "implied_volatility"
                    )
                ),

            "PE_LTP":
                safe_float(
                    pe.get(
                        "last_price"
                    )
                ),

            "PE_PreviousClose":
                safe_float(
                    pe.get(
                        "previous_close_price"
                    )
                ),

            "PE_OI":
                current_pe_oi,

            "PE_ChangeOI":
                pe_change_oi,

            "PE_ChangeMethod":
                pe_change_method,

            "PE_Volume":
                safe_float(
                    pe.get(
                        "volume"
                    )
                ),

            "PE_IV":
                safe_float(
                    pe.get(
                        "implied_volatility"
                    )
                )

        })


    if not rows:

        print(
            "❌ No strike data."
        )

        return None


    # ========================================================
    # SAVE SNAPSHOT
    # ========================================================

    save_current_snapshot(
        current_snapshot
    )


    # ========================================================
    # DATAFRAME
    # ========================================================

    df = pd.DataFrame(
        rows
    )


    df = (
        df
        .sort_values(
            "strike"
        )
        .reset_index(
            drop=True
        )
    )


    # ========================================================
    # ATM
    # ========================================================

    atm_index = (
        df["strike"] - spot
    ).abs().idxmin()


    atm = float(
        df.loc[
            atm_index,
            "strike"
        ]
    )


    # ========================================================
    # ATM ± 5
    # ========================================================

    start = max(
        0,
        atm_index - ATM_RANGE
    )


    end = min(
        len(df),
        atm_index
        +
        ATM_RANGE
        +
        1
    )


    selected = (
        df.iloc[
            start:end
        ]
        .copy()
    )


    # ========================================================
    # TOTALS
    # ========================================================

    ce_oi = selected[
        "CE_OI"
    ].sum()


    pe_oi = selected[
        "PE_OI"
    ].sum()


    ce_change = selected[
        "CE_ChangeOI"
    ].sum()


    pe_change = selected[
        "PE_ChangeOI"
    ].sum()


    ce_volume = selected[
        "CE_Volume"
    ].sum()


    pe_volume = selected[
        "PE_Volume"
    ].sum()


    # ========================================================
    # PCR
    # ========================================================

    if ce_oi > 0:

        pcr = (
            pe_oi /
            ce_oi
        )

    else:

        pcr = 0


    # ========================================================
    # SUPPORT / RESISTANCE
    # ========================================================

    put_support_row = selected.loc[
        selected[
            "PE_OI"
        ].idxmax()
    ]


    call_resistance_row = selected.loc[
        selected[
            "CE_OI"
        ].idxmax()
    ]


    put_support = float(
        put_support_row[
            "strike"
        ]
    )


    call_resistance = float(
        call_resistance_row[
            "strike"
        ]
    )


    # ========================================================
    # CHANGE OI SUPPORT / RESISTANCE
    # ========================================================

    put_change_row = selected.loc[
        selected[
            "PE_ChangeOI"
        ].idxmax()
    ]


    call_change_row = selected.loc[
        selected[
            "CE_ChangeOI"
        ].idxmax()
    ]


    put_change_support = float(
        put_change_row[
            "strike"
        ]
    )


    call_change_resistance = float(
        call_change_row[
            "strike"
        ]
    )


    # ========================================================
    # OI CHANGE METHOD
    # ========================================================

    ce_methods = (
        selected[
            "CE_ChangeMethod"
        ]
        .value_counts()
        .to_dict()
    )


    pe_methods = (
        selected[
            "PE_ChangeMethod"
        ]
        .value_counts()
        .to_dict()
    )


    # ========================================================
    # OPTION CHAIN SCORE
    # ========================================================

    bullish = 0

    bearish = 0


    # ========================================================
    # PCR
    # ========================================================

    if pcr >= 1.00:

        bullish += 2

    elif pcr <= 0.80:

        bearish += 2


    # ========================================================
    # CHANGE OI
    # ========================================================

    if pe_change > ce_change:

        bullish += 2

    elif ce_change > pe_change:

        bearish += 2


    # ========================================================
    # VOLUME
    # ========================================================

    if pe_volume > ce_volume:

        bullish += 1

    elif ce_volume > pe_volume:

        bearish += 1


    # ========================================================
    # BIAS
    # ========================================================

    score_difference = (
        bullish -
        bearish
    )


    if score_difference >= 2:

        bias = "BULLISH"

    elif score_difference <= -2:

        bias = "BEARISH"

    else:

        bias = "MIXED"


    # ========================================================
    # DISPLAY
    # ========================================================

    print(
        "\n=========================================="
    )

    print(
        "OPTION CHAIN SUMMARY"
    )

    print(
        "=========================================="
    )


    print(
        f"Spot       : {spot:.2f}"
    )


    print(
        f"ATM Strike : {atm:.0f}"
    )


    print(
        f"Expiry     : {expiry}"
    )


    print(
        "\nSelected Strikes:"
    )


    print(
        selected[
            "strike"
        ].tolist()
    )


    # ========================================================
    # STRIKE TABLE
    # ========================================================

    print(
        "\n=========================================="
    )

    print(
        "STRIKE-WISE OPTION CHAIN"
    )

    print(
        "=========================================="
    )


    display_columns = [

        "strike",

        "CE_LTP",
        "CE_PreviousClose",

        "CE_OI",

        "CE_ChangeOI",

        "CE_Volume",

        "CE_IV",

        "PE_LTP",
        "PE_PreviousClose",

        "PE_OI",

        "PE_ChangeOI",

        "PE_Volume",

        "PE_IV"

    ]


    print(
        selected[
            display_columns
        ].to_string(
            index=False
        )
    )


    # ========================================================
    # ANALYSIS
    # ========================================================

    print(
        "\n=========================================="
    )

    print(
        "OPTION CHAIN ANALYSIS"
    )

    print(
        "=========================================="
    )


    print(
        f"Total CE OI       : "
        f"{ce_oi:,.0f}"
    )


    print(
        f"Total PE OI       : "
        f"{pe_oi:,.0f}"
    )


    print(
        f"Total CE ChangeOI : "
        f"{ce_change:,.0f}"
    )


    print(
        f"Total PE ChangeOI : "
        f"{pe_change:,.0f}"
    )


    print(
        f"Total CE Volume   : "
        f"{ce_volume:,.0f}"
    )


    print(
        f"Total PE Volume   : "
        f"{pe_volume:,.0f}"
    )


    print(
        f"PCR               : "
        f"{pcr:.2f}"
    )


    print(
        f"\nPut Support       : "
        f"{put_support:.0f}"
    )


    print(
        f"Call Resistance   : "
        f"{call_resistance:.0f}"
    )


    print(
        f"Put ChangeOI Max  : "
        f"{put_change_support:.0f}"
    )


    print(
        f"Call ChangeOI Max : "
        f"{call_change_resistance:.0f}"
    )


    print(
        "\nOI Change Methods:"
    )


    print(
        "CE:",
        ce_methods
    )


    print(
        "PE:",
        pe_methods
    )


    print(
        f"\nBULLISH SCORE     : "
        f"{bullish}"
    )


    print(
        f"BEARISH SCORE     : "
        f"{bearish}"
    )


    print(
        "\nOPTION CHAIN BIAS :",
        bias
    )


    return {

        "spot":
            spot,

        "atm":
            atm,

        "pcr":
            pcr,

        "put_support":
            put_support,

        "call_resistance":
            call_resistance,

        "put_change_support":
            put_change_support,

        "call_change_resistance":
            call_change_resistance,

        "bullish":
            bullish,

        "bearish":
            bearish,

        "bias":
            bias,

        "selected":
            selected

    }


# ============================================================
# FINAL SIGNAL
# ============================================================

def final_signal(option_data):

    print("\n==========================================")
    print("🔥 FINAL TRADE SIGNAL")
    print("==========================================")

    option_bias = option_data["bias"]

    # --------------------------------------------------------
    # PURE OPTION-CHAIN SIGNAL
    # --------------------------------------------------------

    if option_bias == "BULLISH":
        signal = "CALL"

    elif option_bias == "BEARISH":
        signal = "PUT"

    else:
        signal = "NO TRADE"

    option = None
    option_ltp = None
    previous_close = None
    entry = None
    stop_loss = None
    target_1 = None
    target_2 = None

    # --------------------------------------------------------
    # SELECT STRIKE FROM OPTION-CHAIN OI CHANGE
    # --------------------------------------------------------
    # CALL -> strike with maximum positive CE ChangeOI
    # PUT  -> strike with maximum positive PE ChangeOI
    # This keeps the selected option tied to the option-chain
    # activity instead of blindly selecting ATM.
    # --------------------------------------------------------

    selected = option_data["selected"]

    if signal == "CALL":

        option_strike = option_data[
            "call_change_resistance"
        ]

        option_row = selected.loc[
            selected["strike"] == option_strike
        ]

        if option_row.empty:
            signal = "NO TRADE"
        else:
            row = option_row.iloc[0]
            option_ltp = safe_float(row["CE_LTP"])
            previous_close = safe_float(
                row["CE_PreviousClose"]
            )
            option = (
                "NIFTY "
                + str(int(option_strike))
                + " CE"
            )

    elif signal == "PUT":

        option_strike = option_data[
            "put_change_support"
        ]

        option_row = selected.loc[
            selected["strike"] == option_strike
        ]

        if option_row.empty:
            signal = "NO TRADE"
        else:
            row = option_row.iloc[0]
            option_ltp = safe_float(row["PE_LTP"])
            previous_close = safe_float(
                row["PE_PreviousClose"]
            )
            option = (
                "NIFTY "
                + str(int(option_strike))
                + " PE"
            )

    # --------------------------------------------------------
    # OPTION-CHAIN BASED ENTRY / SL / TARGETS
    # --------------------------------------------------------
    # Entry is a trigger above current premium, not CMP entry.
    # SL is the selected option's previous closing price.
    # Risk = Entry - SL.
    # T1 = 2R and T2 = 3R.
    # --------------------------------------------------------

    def round_to_tick(price, tick=0.05):
        return round(round(price / tick) * tick, 2)

    if (
        option
        and option_ltp > 0
        and previous_close > 0
    ):

        entry = round_to_tick(
            option_ltp * (1 + ENTRY_BUFFER_PCT)
        )

        # Previous close must be below entry for a long option trade.
        if previous_close >= entry:
            print(
                "\n⚠️ Previous Close is not below Entry."
            )
            print(
                "Trade setup rejected for safety."
            )
            option = None
            option_ltp = None
            previous_close = None
            entry = None
            stop_loss = None
            target_1 = None
            target_2 = None
            signal = "NO TRADE"

        else:
            stop_loss = round_to_tick(
                previous_close
            )

            risk = entry - stop_loss

            target_1 = round_to_tick(
                entry + (risk * 2)
            )

            target_2 = round_to_tick(
                entry + (risk * 3)
            )

    else:
        option = None
        option_ltp = None
        previous_close = None
        entry = None
        stop_loss = None
        target_1 = None
        target_2 = None

    # --------------------------------------------------------
    # FINAL DISPLAY
    # --------------------------------------------------------

    print(
        "Option Chain :",
        option_bias
    )

    print(
        "\nSignal       :",
        signal
    )

    if option:

        print(
            "Suggested Option   :",
            option
        )

        print(
            f"Option LTP         : {option_ltp:.2f}"
        )

        print(
            f"Previous Close     : {previous_close:.2f}"
        )

        print(
            f"Entry              : {entry:.2f}"
        )

        print(
            f"Stop Loss          : {stop_loss:.2f}"
        )

        print(
            f"Target 1           : {target_1:.2f}"
        )

        print(
            f"Target 2           : {target_2:.2f}"
        )

        print(
            "\n📌 ENTRY RULE"
        )

        print(
            "Wait for option premium to reach the calculated entry level."
        )

        print(
            "Do NOT enter simply at current CMP."
        )

    else:

        print("Suggested Option   : NO TRADE")
        print("Option LTP         : -")
        print("Previous Close     : -")
        print("Entry              : -")
        print("Stop Loss          : -")
        print("Target 1           : -")
        print("Target 2           : -")

    print(
        "\n⚠️ Automated rule-based analysis. Not a guaranteed trade."
    )

    return {

        "Time": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "Spot": option_data["spot"],
        "ATM": option_data["atm"],
        "PCR": option_data["pcr"],
        "Put_Support": option_data["put_support"],
        "Call_Resistance": option_data["call_resistance"],
        "Put_ChangeOI_Support": option_data[
            "put_change_support"
        ],
        "Call_ChangeOI_Resistance": option_data[
            "call_change_resistance"
        ],
        "Bullish_Score": option_data["bullish"],
        "Bearish_Score": option_data["bearish"],
        "Option_Bias": option_bias,
        "Signal": signal,
        "Suggested_Option": option,
        "Option_LTP": option_ltp,
        "Previous_Close": previous_close,
        "Entry": entry,
        "Stop_Loss": stop_loss,
        "Target_1": target_1,
        "Target_2": target_2

    }


# ============================================================
# MAIN
# ============================================================

expiries = get_expiries()


if not expiries:

    print(
        "\n❌ NIFTY expiry dates nahi mili."
    )

    print(
        "Program safely stopped."
    )

    raise SystemExit


# ============================================================
# EXPIRY LIST
# ============================================================

print(
    "\nAvailable expiries:"
)


for number, expiry in enumerate(

    expiries,

    start=1

):

    print(
        f"{number}. {expiry}"
    )


# ============================================================
# NEAREST EXPIRY
# ============================================================

nearest_expiry = expiries[0]


print(
    "\n=========================================="
)

print(
    "SELECTED EXPIRY"
)

print(
    "=========================================="
)

print(
    nearest_expiry
)


# ============================================================
# OPTION CHAIN
# ============================================================

option_response = get_option_chain(

    nearest_expiry

)


if option_response is None:

    print(
        "\n❌ Option Chain data nahi mila."
    )

    print(
        "\nPossible reason:"
    )

    print(
        "1. Dhan API temporary issue"
    )

    print(
        "2. Access token issue"
    )

    print(
        "3. API rate-limit"
    )

    print(
        "4. API backend unavailable"
    )

    print(
        "\nProgram stopped safely."
    )

    raise SystemExit


# ============================================================
# PARSE
# ============================================================

option_data = parse_option_chain(

    option_response,

    nearest_expiry

)


if option_data is None:

    print(
        "\n❌ Option Chain parse nahi hua."
    )

    raise SystemExit


# ============================================================
# FINAL SIGNAL
# ============================================================

result = final_signal(

    option_data,

    candles

)


# ============================================================
# SAVE CSV
# ============================================================

try:

    pd.DataFrame(
        [result]
    ).to_csv(

        "trade_burner_final_signal.csv",

        index=False

    )


    print(
        "\nSaved: "
        "trade_burner_final_signal.csv ✅"
    )


except PermissionError:

    filename = (

        "trade_burner_final_signal_"
        +
        datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        +
        ".csv"

    )


    pd.DataFrame(
        [result]
    ).to_csv(

        filename,

        index=False

    )


    print(
        f"\nCSV was open."
        f" Saved as {filename} ✅"
    )


# ============================================================
# COMPLETE
# ============================================================

print(
    "\n=========================================="
)

print(
    "TRADE BURNER ANALYZER COMPLETE ✅"
)

print(
    "=========================================="
)