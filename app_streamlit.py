# app_final_analytics.py
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
            "Плече": leverage
        })
        current_price *= (1 + price_step_pct / 100)
        added_laz *= (1 + laz_increase_pct / 100)
    
    return pd.DataFrame(steps)


def recalculate_strategy(df: pd.DataFrame):
    """Повністю перераховує всі залежні стовпчики на основі відредагованих даних."""
    
    new_df = df.copy()

    # Визначаємо початкову ціну для розрахунку загального захисту
    initial_start_price = new_df.loc[0, 'Ціна входу ($)'] if not new_df.empty else 0

    # ... (решта коду функції)
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
        
        avg_price = total_value / total_laz if total_laz > 0 else 0
        liquidation_price = 0
        if total_margin > 0:
            effective_leverage = total_value / total_margin
            liquidation_price = avg_price * (1 + 1 / effective_leverage)

        # --- РОЗРАХУНОК НОВИХ СТОВПЧИКІВ ---
        safety_margin_percent = ((liquidation_price - price) / price) * 100 if price > 0 else 0
        total_protection_percent = ((liquidation_price - initial_start_price) / initial_start_price) * 100 if initial_start_price > 0 else 0
        status = "✅ Безпечно" if liquidation_price > price else "❌ Небезпечно"
        
        new_df.loc[i, 'Розмір доданої позиції ($)'] = round(added_size_usd, 2)
        new_df.loc[i, 'Маржа додана на кроці ($)'] = round(added_margin, 2)
        new_df.loc[i, 'Загальна вкладена маржа ($)'] = round(total_margin, 2)
        new_df.loc[i, "Загальний об'єм LAZ"] = round(total_laz, 2)
        new_df.loc[i, 'Середня ціна входу ($)'] = round(avg_price, 4)
        new_df.loc[i, 'Ціна ліквідації ($)'] = round(liquidation_price, 4)
        new_df.loc[i, 'Стан входу'] = status
        new_df.loc[i, 'Запас від входу (%)'] = f"{safety_margin_percent:.1f}%"
        new_df.loc[i, 'Загальний захист (%)'] = f"{total_protection_percent:.1f}%"
        
    return new_df


# --- ІНТЕРФЕЙС STREAMLIT ---
st.title("⚡ Динамічний 'What-If' Симулятор Стратегії")

with st.sidebar:
    st.header("Генератор початкової сітки")
    st.write("Ці параметри створять таблицю за замовчуванням. Потім ви зможете редагувати будь-який крок вручну.")
    
    num_steps = st.number_input("Кількість кроків", min_value=5, max_value=100, value=20)
    start_price = st.number_input("Початкова ціна ($)", value=0.5, format="%.4f")
    price_step_pct = st.number_input("Крок ціни (%)", value=2.0)
    start_laz = st.number_input("Стартова кількість LAZ", value=2.0)
    laz_increase_pct = st.number_input("Збільшення LAZ на кроці (%)", value=20.0)
    leverage = st.number_input("Плече (для всіх кроків)", value=1.5, format="%.1f")

    if st.button("Сгенерувати / Скинути", type="primary"):
        initial_df = generate_initial_data(start_price, price_step_pct, start_laz, laz_increase_pct, leverage, num_steps)
        st.session_state.strategy_df = initial_df
        st.rerun()

if 'strategy_df' not in st.session_state or st.session_state.strategy_df.empty:
    st.info("Натисніть 'Сгенерувати / Скинути' на бічній панелі, щоб створити початкову таблицю.")
else:
    recalculated_df = recalculate_strategy(st.session_state.strategy_df)
    last_step = recalculated_df.iloc[-1]
    
    # --- ОНОВЛЕНИЙ ДАШБОРД ---
    st.header("📈 Підсумковий стан позиції")
    cols = st.columns(5)
    cols[0].metric("Середня ціна входу", f"${last_step['Середня ціна входу ($)']:.4f}")
    cols[1].metric("Ціна ліквідації", f"${last_step['Ціна ліквідації ($)']:.4f}")
    cols[2].metric("Загальна маржа", f"${last_step['Загальна вкладена маржа ($)']:.2f}")
    cols[3].metric("Загальний захист (%)", last_step['Загальний захист (%)'], help="На скільки % ціна має зрости від найпершого входу, щоб ліквідувати всю позицію.")
    cols[4].metric("Загальний об'єм (LAZ)", f"{last_step['Загальний об\'єм LAZ']:.2f}")
    
    st.divider()
    
    # --- ІНТЕРАКТИВНА ТАБЛИЦЯ ---
    st.header("Інтерактивна таблиця стратегії")
    
    # Визначаємо, які стовпчики будуть відображатись і які будуть заблоковані
    display_columns = [
        "№ Кроку", "Ціна входу ($)", "Об'єм LAZ доданий", "Плече", "Стан входу",
        "Маржа додана на кроці ($)", "Загальна вкладена маржа ($)", "Загальний об'єм LAZ",
        "Середня ціна входу ($)", "Ціна ліквідації ($)", "Запас від входу (%)", "Загальний захист (%)"
    ]
    disabled_columns = [col for col in display_columns if col not in ["Ціна входу ($)", "Об'єм LAZ доданий", "Плече"]]

    edited_df = st.data_editor(
        recalculated_df[display_columns], # Відображаємо тільки потрібні стовпчики
        disabled=disabled_columns,
        num_rows="dynamic",
        hide_index=True,
        key="data_editor"
    )

    if not edited_df.equals(st.session_state.strategy_df[display_columns]):
        # Оновлюємо тільки ті стовпчики, які користувач міг змінити
        st.session_state.strategy_df['Ціна входу ($)'] = edited_df['Ціна входу ($)']
        st.session_state.strategy_df['Об\'єм LAZ доданий'] = edited_df['Об\'єм LAZ доданий']
        st.session_state.strategy_df['Плече'] = edited_df['Плече']
        st.rerun()
