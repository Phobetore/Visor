# VISOR 🛰️

**Visual Interactive System for Observing Network Traffic**

Visor est un outil de visualisation du trafic réseau en temps réel, conçu pour rendre les communications réseau compréhensibles, visuelles et dynamiques. L’objectif est de fournir une interface moderne et intuitive pour observer les flux, détecter les anomalies, et apprendre par l’image comment circule l’information.

---

## 📌 Objectifs

- Visualiser les flux réseau en temps réel (IP source/destination, ports, protocoles…)
- Afficher les connexions sous forme de **graphes dynamiques**
- Géolocaliser les IP et représenter le trafic sur une carte
- Détecter et signaler des anomalies simples (trafic inhabituel, ports suspects…)
- Fournir un outil éducatif et démonstratif pour étudiants, pentesters, analystes réseau
- Interface web cyberpunk pour la visualisation

---

## 📷 Aperçu (à venir)

> Des captures d’écran et démos seront ajoutées dès les premières versions MVP.

---

## ⚙️ Stack technique prévue

| Composant         | Choix préliminaire               |
|-------------------|----------------------------------|
| Langage backend   | Python 3                         |
| Capture réseau    | [Scapy](https://scapy.net/)     |
| API               | FastAPI                          |
| Frontend          | D3.js                             |
| Base de données   | SQLite ou stockage JSON         |
| Géolocalisation   | IP2Location / GeoLite2          |
| Visualisation     | WebSocket + affichage dynamique |

---

## 🚀 Lancer le projet

> **Pré-requis :**
> - Python 3.10+
> - `virtualenv`
- Node.js (optionnel, non requis pour la version actuelle)

```bash
git clone https://github.com/Phobetore/Visor.git
cd visor
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Lancement de l'API
python main.py
# Puis ouvrez http://localhost:8000 pour l'interface cyberpunk
```

### Utilisateurs Windows

- Installez [Npcap](https://npcap.com/) en mode compatible **WinPcap**.
- Lancez `python main.py` depuis un terminal **Administrateur**.

> **Pas de paquets ?** Vérifiez que Npcap est bien installé et qu'aucun antivirus ou pare-feu ne bloque la capture.

Une fois le serveur lancé, l'interface communique en temps réel via WebSocket
pour afficher un graphe dynamique des paquets capturés. Les liens sont filtrés
pour éviter les doublons et garder la visualisation lisible. Laissez tourner la
capture quelques instants et observez l’évolution du réseau !

---

## 📍 Roadmap

| Phase | Objectifs | Statut |
|-------|-----------|--------|
| ✅ Phase 0 | Initialisation du dépôt, README, structure de base | ✔️ |
| 🔧 Phase 1 | Capture réseau minimale (Scapy ou pcap) + log | ✔️ |
| 🔧 Phase 2 | API REST (FastAPI) exposant les flux | ✔️ |
| 🔧 Phase 3 | Frontend minimal affichant les connexions | ✔️ |
| 🔧 Phase 4 | Visualisation dynamique (D3.js) | ✔️ |
| 🔧 Phase 5 | Détection d’anomalies réseau basiques | 🔜 |
| 🌐 Phase 6 | Géolocalisation des IP et affichage sur carte | 🔜 |
| 📦 Phase 7 | Export JSON / PNG / GIF des sessions | 🔜 |

---

## 🧪 Fonctionnalités futures (idées)

- Simulation de flux pour test (lecture de `.pcap`)
- Mode “demo pédagogique” pour expliquer un paquet
- Intégration Shodan / AbuseIPDB pour enrichissement IP
- Export rapport Markdown / PDF
- Interface CLI alternative
- Plugin Splunk / ELK pour export

---

## 🤝 Contribuer

> Ce projet est encore au tout début. Toute contribution est bienvenue : idées, UI, scripts, données, etc.

1. Fork le repo
2. Crée une branche (`git checkout -b feature/ta-feature`)
3. Commits propres avec messages clairs
4. Pull request documentée

---

## 📝 Licence

MIT – fais-en bon usage, améliore-le, partage.

---

## 👨‍💻 Auteur

Projet initié par **core.layer**/**Phobetore** 
Alternant en cybersécurité | Passionné de Dev/Cyber | Offensive & defensive mindset
