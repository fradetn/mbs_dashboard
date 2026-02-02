import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from collections import Counter


st.set_page_config(
	page_title="Dashboard eSIM - MyBestSim",
	page_icon="📟",
	layout="wide"
)


CSV_BASE_URL = "http://d4ow8gwkc800w4o44c8oo8ck.31.97.154.190.sslip.io"

@st.cache_data(ttl=3600)
def list_provider_files(base_url):
	"""
	Liste dynamiquement tous les fichiers de fournisseurs sur le serveur.
	"""
	try:
		response = requests.get(base_url + "/csv/", timeout=10)
		response.raise_for_status()
		
		soup = BeautifulSoup(response.text, "html.parser")
		
		
		providers = []
		
		# Méthode 1 : Chercher tous les <a> tags
		for link in soup.find_all("a"):
			href = link.get("href")
			
			# Filtrer : doit être un lien, pas "../" ou "/", doit contenir du texte
			if href and href not in ["../", "/", "", "/csv"]:
				
				new_response = requests.get(base_url + href, timeout=10)
				new_response.raise_for_status()

				new_soup = BeautifulSoup(new_response.text, "html.parser")
				# st.write(new_soup.find_all("a"))
				for l in new_soup.find_all("a"):
					new_href = l.get("href")
					if new_href and new_href.__contains__("Plans.csv"):
						clean_name = new_href.rstrip("/")
						providers.append(clean_name)
		
		# Dédupliquer et trier
		providers = sorted(list(set(providers)))
		
		return providers
    
	except Exception as e:
		st.error(f"Erreur lors du listing des fournisseurs : {str(e)}")
	return []


PROVIDERS  = list_provider_files(CSV_BASE_URL)

# ==================================== FONCTIONS D'EXTRACTION DES DONNEES ====================================
@st.cache_data(ttl=3600)
def load_data_from_csv():
	"""
	Lis chaque fichiers depuis son lien pour extraire son contenu
	dans un dataFrane.
	"""
	all_data = []
	for index in range(0, len(PROVIDERS)):
		try:
			csv_url = CSV_BASE_URL + PROVIDERS[index]
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


@st.cache_data(ttl=3600)
def sanitize_data_type(dataframe):
    """
    Uniformise les types des colonnes importantes.
    """
    df = dataframe.copy()  # Toujours travailler sur une copie
    
    # Nettoyer PRIX/GB(EUR)
    df['PRIX/GB(EUR)'] = df['PRIX/GB(EUR)'].apply(
        lambda x: float(str(x).replace(',', '.')) if pd.notna(x) else None
    )
    
    return df

# ==================================== Preparation des donnees ====================================
# all_products = load_data_from_csv()

all_products =  sanitize_data_type(load_data_from_csv())


nb_produits = len(all_products)

price_range_df = (
    all_products
    .groupby("NOM ENTREPRISE")["PRIX"]
    .agg(
        min_price="min",
        max_price="max"
    )
    .reset_index()
)

products_count_df = (
    all_products
    .groupby("NOM ENTREPRISE")
    .size()
    .reset_index(name="nb_produits")
)

provider_avg_df = (
    all_products
    .groupby("NOM ENTREPRISE")
    .agg(
        avg_price=("PRIX", "mean"),
        avg_data_go=("DONNEES (GO)", "mean")
    )
    .reset_index()
)

price_per_data_df = (
    all_products
    .groupby("NOM ENTREPRISE")
    .agg(
        avg_price_per_data=("PRIX/GB(EUR)", "mean"),
    )
    .reset_index()
)
price_per_data_df = price_per_data_df.sort_values('avg_price_per_data')

# Extraire tous les pays
all_countries = []
for countries_str in all_products['COUVERTURE'].dropna():
    countries = [c.strip() for c in str(countries_str).split(',')]
    all_countries.extend(countries)

# Compter les occurrences
country_counts = Counter(all_countries)
top_10_countries = pd.DataFrame(
    country_counts.most_common(10),
    columns=['Pays', 'Nombre de produits']
)

# ==================================== Dashboard : Creation des graphiques ====================================

# Compter les produits et les produits > 100€
nb_products_100_more = len(all_products[all_products['PRIX'] > 100])

# products_info : le graphique pour les produits > 100€
products_info_fig = go.Figure(data=[go.Pie(
    labels=['≤ 100€', '> 100€'],
    values=[nb_produits - nb_products_100_more, nb_products_100_more],
    hole=0.6,
    textinfo='value',
    textfont_size=19,
    marker=dict(
        colors=['#8b5cf6', '#c4b5fd'],
        line=dict(color='white', width=2)
    ),
    hovertemplate='<b>%{label}</b><br>%{value} produits<br>%{percent}<extra></extra>'
)])

# Layout responsive
products_info_fig.update_layout(
    legend=dict(
        title=dict(
            text="Prix des produits",
            font=dict(size=13),
        ),
        font=dict(size=12),
        orientation="h",
		x=0.5,
		y=0,
		yanchor="top",
		xanchor="center",
    ),
    showlegend=True,
  	height=250,
    margin=dict(t=20, b=20, l=10, r=10),  # Marges proportionnelles
)

# Annotation centrale
products_info_fig.add_annotation(
    text=f"<b>{nb_produits:,}</b><br><span style='font-size:0.8em'>produits total</span>",
    x=0.5, y=0.5,
    font=dict(size=14),
    showarrow=False
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

prod_per_providers_fig = go.Figure()

prod_per_providers_fig.add_trace(
    go.Bar(
        x=products_count_df["NOM ENTREPRISE"],
        y=products_count_df["nb_produits"],
        text=products_count_df["nb_produits"],
        textposition="outside",
        hovertemplate=(
            "Fournisseur: %{x}<br>"
            "Nombre d'offres: %{y}<extra></extra>"
        ),
        name="Nombre d'offres"
    )
)

prod_per_providers_fig.update_layout(
    xaxis_title="Fournisseur",
    yaxis_title="Nombre d'offres",
    height=390,
    margin=dict(t=0, b=0, l=0, r=0)
)

global_avg_price = all_products["PRIX"].mean()
global_avg_data = all_products["DONNEES (GO)"].mean()

avg_price_fig = go.Figure()

avg_price_fig.add_trace(
    go.Scatter(
        x=provider_avg_df["avg_price"],
        y=provider_avg_df["NOM ENTREPRISE"],
        mode="markers",
        name="Prix moyen",
        marker=dict(size=10),
        hovertemplate="%{y}<br>Prix moyen: %{x:.2f} €<extra></extra>"
    )
)

# Ligne de moyenne globale
avg_price_fig.add_vline(
    x=global_avg_price,
    line_dash="dash",
    line_color="red"
)

# Annotation moyenne globale
avg_price_fig.add_annotation(
    x=global_avg_price,
    y=-0.5,
    text=f"Moyenne globale: {global_avg_price:.2f} €",
    showarrow=False,
    xanchor="center",
    yanchor="top"
)

avg_price_fig.update_layout(
    title="Prix moyen (€) par fournisseur",
    height=510,
    showlegend=False,
    margin=dict(t=40, b=0, l=0, r=0)
)
avg_data_fig = go.Figure()

avg_data_fig.add_trace(
    go.Scatter(
        x=provider_avg_df["avg_data_go"],
        y=provider_avg_df["NOM ENTREPRISE"],
        mode="markers",
        name="Data moyenne",
        marker=dict(size=10),
        hovertemplate="%{y}<br>Data moyenne: %{x:.2f} Go<extra></extra>"
    )
)

# Ligne de moyenne globale
avg_data_fig.add_vline(
    x=global_avg_data,
    line_dash="dash",
    line_color="red"
)

# Annotation moyenne globale
avg_data_fig.add_annotation(
    x=global_avg_data,
    y=-0.5,
    text=f"Moyenne globale: {global_avg_data:.2f} Go",
    showarrow=False,
    xanchor="center",
    yanchor="top"
)

avg_data_fig.update_layout(
    title="Data moyenne (Go) par fournisseur",
    height=510,
    showlegend=False,
    margin=dict(t=40, b=0, l=0, r=0)
)



provider_price_per_data_fig = go.Figure()

provider_price_per_data_fig.add_trace(
    go.Bar(
        x=price_per_data_df["NOM ENTREPRISE"], 
        y=price_per_data_df["avg_price_per_data"],
        text=price_per_data_df["avg_price_per_data"].round(2),  # Arrondir à 2 décimales
        texttemplate='%{text:.2f}€/GB',  # Format avec €/GB
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Prix moyen: <b>%{y:.2f}€/GB</b>"
            "<extra></extra>"
        ),
        name="Prix moyen du GB",
        marker=dict(
            color=price_per_data_df["avg_price_per_data"],
            colorscale='RdYlGn_r',  # Rouge (cher) → Vert (pas cher)
            showscale=True,
            colorbar=dict(title="€/GB")
        )
    )
)

# Layout
provider_price_per_data_fig.update_layout(
    xaxis_title="Fournisseur",
    yaxis_title="Prix/GB (€)",
    height=460,
    showlegend=False,
    hovermode='x unified',
	margin=dict(t=20, b=0, l=0, r=0)
)


top_10_countries = top_10_countries.sort_values('Nombre de produits', ascending=True)

# Créer le graphique avec graph_objects
top_10_countries_fig = go.Figure()

top_10_countries_fig.add_trace(go.Bar(
    x=top_10_countries['Nombre de produits'],
    y=top_10_countries['Pays'],
    orientation='h',
    marker=dict(
        color=top_10_countries['Nombre de produits'],
        colorscale='Blues',
        showscale=True,
        colorbar=dict(
            title="Produits",
            thickness=10,
            len=0.5
        )
    ),
    text=top_10_countries['Nombre de produits'],
    texttemplate='%{text}',
    textposition='inside',
    hovertemplate='<b>%{y}</b><br>%{x} produits<extra></extra>'
))

# Layout
top_10_countries_fig.update_layout(
    xaxis_title="Nombre de produits",
    yaxis_title="",
    height=510,
    showlegend=False,
    margin=dict(t=0, b=0, l=0, r=0)
)

# ==================================== Dashboard : Affichage des graphiques  ====================================

# ============ TITRE ============
st.title("Dashboard eSIM - MyBestSim", text_alignment="center")
st.space("medium")

col_large, col_small = st.columns([2, 1], gap="small")
with col_large:
	with st.container(border=True, height="content"):
		st.markdown("**📊 Produits par Fournisseur**")
		st.plotly_chart(prod_per_providers_fig, use_container_width=True)
	with st.container(border=True, height="content", width="stretch"):
		st.markdown("**💰 Prix Moyen du GB par Fournisseur**")
		st.plotly_chart(provider_price_per_data_fig, use_container_width=True)		
with col_small:
	with st.container(border=True, height="content"):
		st.markdown("**💎 Nombre de Produits**")
		st.plotly_chart(products_info_fig, use_container_width=True)
	with st.container(border=True, height="content", width="stretch"):
		st.markdown("**💵 Fourchette de Prix**")
		st.dataframe(styled_df, 
		height=600,
		use_container_width=True)

col_small, col_large = st.columns([1, 2], gap="small")
with col_large:
	with st.container(border=True, height="content"):
		st.markdown("**➡ Moyennes par fournisseur vs moyennes globales**")
		col1, col2= st.columns(2, gap="small")
		with col1:
			with st.container(border=False, height="content"):
				st.plotly_chart(avg_price_fig, use_container_width=True)
		with col2:
			with st.container(border=False, height="content"):
				st.plotly_chart(avg_data_fig, use_container_width=True)
with col_small:
	with st.container(border=True, height="content"):
		st.markdown("**🌍 Top 10 Pays les Plus Couverts**")
		st.plotly_chart(top_10_countries_fig, use_container_width=True)
