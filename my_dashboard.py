import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Dashboard eSIM - MyBestSim",
    page_icon="📊",
    layout="wide"
)

CSV_BASE_URL = "http://d4ow8gwkc800w4o44c8oo8ck.31.97.154.190.sslip.io/csv/"

PROVIDERS  = ["Airalo", "Esim4Travel", "ezyEsim", "Instabridge", "redtea", "yesim", "amigo", "esimo", "ezyesim", "maya", "saily", "breeze", "eSIMX", "gigsky", "microEsim", "Ubigi"]
PROVIDERSPLANS  = ["AiraloPlans", "Esim4TravelPlans", "ezyEsimPlans", "InstabridgePlans", "redteaPlans", "yesimPlans", "amigoPlans", "esimoPlans", "ezyEsimPlans", "mayaPlans", "sailyPlans", "breezePlans", "eSIMXPlans", "gigskyPlans", "microEsimPlans", "UbigiPlans"]

# ============ FONCTIONS D'EXTRACTION DES DONNEES ============
@st.cache_data(ttl=3600)
def load_data_from_csv():
	all_data = []
	for index in range(0, 16):
		try:
			csv_url = CSV_BASE_URL + PROVIDERS[index] + "/" + PROVIDERSPLANS[index] + ".csv"
			df = pd.read_csv(csv_url)

			all_data.append(df)

		except Exception as e:
			st.sidebar.error("❌ Erreur "+ csv_url + ":"+ str(e))
			continue
	if all_data:
		combined_df = pd.concat(all_data, ignore_index=True)
		return combined_df
	else:
		st.error("Aucune donnée chargée !")
		return pd.DataFrame()


all_products = load_data_from_csv()
st.sidebar.title("🔍 Filtres")

nb_produits = len(all_products)

# ============ DEBUG : Inspecter les données ============
# st.write("### 🔍 Debug : Structure des données")
# st.write("**Colonnes disponibles :**", all_products.columns.tolist())
# st.write("**Premières lignes :**")
# st.dataframe(all_products.head(10))

# # Voir les types de données
# st.write("**Types de colonnes :**")
# st.write(all_products.dtypes)

# ============ Dashboard : Creation des graphiques ============

# Compter les produits et les produits > 100€
nb_produits_100_plus = len(all_products[all_products['PRIX'] > 100])

# products_info : le graphique pour les produits > 100€
products_info = go.Figure(data=[go.Pie(labels=['≤ 100€', '> 100€'],
	values=[nb_produits - nb_produits_100_plus, nb_produits_100_plus])])

products_info.update_traces(hoverinfo='label+percent', 
 	hole=0.6,
	textinfo='value',
	textfont_size=19,
	marker=dict(colors=['#8b5cf6', '#c4b5fd'], line=dict(color='white', width=2)),
	hovertemplate='<b>%{label}</b><br>%{value} produits<br>%{percent}<extra></extra>'
	)

products_info.update_layout(
    title={
        'text': "📊 Répartition des Produits par Prix",
        'x': 0.5,
        'xanchor': 'center'
    },
	legend=dict(
		title=dict(
			text= "Prix des produits",
			font=dict(
				size=17,
        	),
        ),
		font=dict(
            size=15,
        )
	),
	title_font=dict(size=25),
    showlegend=True,
    height=400,
    margin=dict(t=80, b=20, l=20, r=20)
)

products_info.add_annotation(
    text=f"<b>{nb_produits:,}</b><br><span style='font-size:14px'>produits total</span>",
    x=0.5, y=0.5,
    font=dict(size=24),
    showarrow=False
)

price_range_df = (
    all_products
    .groupby("NOM ENTREPRISE")["PRIX"]
    .agg(
        min_price="min",
        max_price="max"
    )
    .reset_index()
)

global_min_price = price_range_df["min_price"].min()
global_max_price = price_range_df["max_price"].max()

# highlight_extremes : affiche les valeurs extremes dans le tableau
def highlight_extremes(row):
    styles = [""] * len(row)

    if row["min_price"] == global_min_price:
        styles[row.index.get_loc("min_price")] = (
            "background-color: #d1fae5; color: #065f46; font-weight: bold;"
        )

    if row["max_price"] == global_max_price:
        styles[row.index.get_loc("max_price")] = (
            "background-color: #fee2e2; color: #991b1b; font-weight: bold;"
        )

    return styles

#styled_df : le tableau stylise
styled_df = (
    price_range_df
    .style
    .apply(highlight_extremes, axis=1)
    .format({
        "min_price": "{:.2f} €",
        "max_price": "{:.2f} €",
    })
)

# ============ Dashboard : Affichage des graphiques  ============

col1, col2 = st.columns(2)
with col1:
	with st.container(border=True):
		st.plotly_chart(products_info, use_container_width=True)
with col2:
	with st.container(border=True):
		st.subheader("📊 Fourchette de prix par fournisseur")
		st.caption("Prix minimum et maximum observés dans le catalogue")
		st.dataframe(styled_df, 
		height=400,
		use_container_width=True)


