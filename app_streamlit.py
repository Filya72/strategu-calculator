# app_editable_grid_with_status.py
import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")


# --- ФУНКЦІЇ ---

def generate_initial_data(start_price, price_step_pct, start_laz, laz_increase_pct, leverage, num_steps):
    """Генерує початковий DataFrame на основі заданих правил."""
    steps = []
    current_price = start_price
    added_laz = start_laz

    for i in range(1, num_steps + 1):
        steps.append({
            "№ Кроку": i,
            "Ціна входу ($)": current_price,
            "Об'єм LAZ доданий": round(added_laz, 2),
            "Плече": leverage,
            "Стан входу": ""  # Додаємо пустий стовпчик
        })
        current_price *= (1 + price_step_pct / 100)
        added_laz *= (1 + laz_increase_pct / 100)

    return pd.DataFrame(steps)


def recalculate_strategy(df: pd.DataFrame):
    """Повністю перераховує всі залежні стовпчики на основі відредагованих даних."""

    new_df = df.copy()

    calculated_columns = [
        "Розмір доданої позиції ($)", "Маржа додана на кроці ($)",
        "Загальна вкладена маржа ($)", "Загальний об'єм LAZ", "Загальний об'єм ($)",
        "Середня ціна входу ($)", "Ціна ліквідації ($)", "Стан входу"
    ]

    for col in calculated_columns:
        if col not in new_df:
            new_df[col] = 0.0

    total_margin = 0.0
    total_laz = 0.0
    total_value = 0.0

    for i, row in new_df.iterrows():
        price = row['Ціна входу ($)']
        laz_added = row["Об'єм LAZ доданий"]
        leverage = row['Плече']

        added_size_usd = laz_added * price
        added_margin = added_size_usd / leverage

        total_margin += added_margin
        total_laz += laz_added
        total_value += added_size_usd

        if total_laz == 0:
            avg_price = 0
            liquidation_price = 0
        else:
            avg_price = total_value / total_laz
            if total_margin > 0:
                effective_leverage = total_value / total_margin
                liquidation_price = avg_price * (1 + 1 / effective_leverage)
            else:
                liquidation_price = float('inf')

        # --- ЛОГІКА ДЛЯ НОВОГО СТОВПЧИКА ---
        if liquidation_price > price:
            status = "✅ Безпечно"
        else:
            status = "❌ Небезпечно"
        # ------------------------------------

        new_df.loc[i, 'Розмір доданої позиції ($)'] = round(added_size_usd, 2)
        new_df.loc[i, 'Маржа додана на кроці ($)'] = round(added_margin, 2)
        new_df.loc[i, 'Загальна вкладена маржа ($)'] = round(total_margin, 2)
        new_df.loc[i, "Загальний об'єм LAZ"] = round(total_laz, 2)
        new_df.loc[i, "Загальний об'єм ($)"] = round(total_value, 2)
        new_df.loc[i, 'Середня ціна входу ($)'] = round(avg_price, 4)
        new_df.loc[i, 'Ціна ліквідації ($)'] = round(liquidation_price, 4)
        new_df.loc[i, 'Стан входу'] = status  # Записуємо статус

    return new_df


# --- ІНТЕРФЕЙС STREAMLIT ---

st.title("⚡ Динамічний 'What-If' Симулятор Стратегії")

with st.sidebar:
    st.header("Генератор початкової сітки")
    st.write("Ці параметри створять таблицю за замовчуванням. Потім ви зможете редагувати будь-який крок вручну.")

    num_steps = st.number_input("Кількість кроків", min_value=5, max_value=100, value=20)
    start_price = st.number_input("Початкова ціна ($)", value=0.5, format="%.4f")
    price_step_pct = st.number_input("Крок ціни (%)", value=1.0,
                                     help="Крок ціни між усередненнями")  # Змінив крок на 1% для кращої демонстрації
    start_laz = st.number_input("Стартова кількість LAZ", value=2.0)
    laz_increase_pct = st.number_input("Збільшення LAZ на кроці (%)", value=20.0)
    leverage = st.number_input("Плече (для всіх кроків)", value=1.5, format="%.1f")

    if st.button("Сгенерувати / Скинути", type="primary"):
        initial_df = generate_initial_data(start_price, price_step_pct, start_laz, laz_increase_pct, leverage,
                                           num_steps)
        st.session_state.strategy_df = initial_df
        st.rerun()

if 'strategy_df' not in st.session_state or st.session_state.strategy_df.empty:
    st.info("Натисніть 'Сгенерувати / Скинути' на бічній панелі, щоб створити початкову таблицю.")
else:
    st.header("📈 Підсумковий стан позиції")

    recalculated_df = recalculate_strategy(st.session_state.strategy_df)
    last_step = recalculated_df.iloc[-1]

    cols = st.columns(5)
    cols[0].metric("Середня ціна входу", f"${last_step['Середня ціна входу ($)']:.4f}")
    cols[1].metric("Ціна ліквідації", f"${last_step['Ціна ліквідації ($)']:.4f}",
                   help="Якщо ціна досягне цього рівня, вся позиція буде ліквідована.")
    cols[2].metric("Загальна маржа", f"${last_step['Загальна вкладена маржа ($)']:.2f}",
                   help="Сума ваших власних коштів, задіяних у позиції.")
    cols[3].metric("Загальний об'єм ($)", f"${last_step['Загальний об\'єм ($)']:.2f}",
                   help="Загальна номінальна вартість позиції.")
    cols[4].metric("Загальний об'єм (LAZ)", f"{last_step['Загальний об\'єм LAZ']:.2f}")

    st.divider()

    st.header("Інтерактивна таблиця стратегії")
    st.write(
        "Клікайте на комірки в стовпчиках `Ціна входу`, `Об'єм LAZ` або `Плече`, щоб змінити їх. Дашборд та розрахунки оновляться автоматично.")

    # Додаємо новий стовпчик до списку нередагованих
    disabled_columns = [
        "№ Кроку", 'Розмір доданої позиції ($)', 'Маржа додана на кроці ($)',
        'Загальна вкладена маржа ($)', "Загальний об'єм LAZ", "Загальний об'єм ($)",
        'Середня ціна входу ($)', 'Ціна ліквідації ($)', 'Стан входу'
    ]

    edited_df = st.data_editor(
        recalculated_df,
        disabled=disabled_columns,
        num_rows="dynamic",
        hide_index=True,
        key="data_editor"
    )

    if not edited_df.equals(st.session_state.strategy_df):
        st.session_state.strategy_df = edited_df
        st.rerun()