# Recolector Termux — SOLV/XRP/BTC

Replica la lógica actual del bridge de Windows y escribe en los mismos Apps Script.

## Seguridad
`config.json` contiene los dos Web App URLs y Shared Secrets. Está ignorado por Git y NO debe subirse al repositorio.

## Instalación resumida
```sh
pkg update -y
pkg install python git nano -y
cd ~
git clone https://github.com/rayogammma432-gif/solv-xrp-market-data.git
cd ~/solv-xrp-market-data/termux
python -m pip install -r requirements-termux.txt
cp config.example.json config.json
nano config.json
chmod +x start_collector.sh stop_collector.sh status_collector.sh
```

En `config.json`, copiar los valores actuales desde `config.ps1` (SOLV) y `config_xrp.ps1` (XRP). No compartirlos en chats ni subirlos a GitHub.

## Pruebas
Sin escribir en Sheets:
```sh
python market_collector.py --dry-run
```

Prueba real única:
```sh
python market_collector.py
```

## Ejecución 24/7
```sh
./start_collector.sh
./status_collector.sh
./stop_collector.sh
```

El scheduler hace una ejecución inmediata al arrancar y luego opera aproximadamente en :01, :16, :31 y :46, un minuto después de cada cierre de vela 15m.

## Inicio automático con Termux:Boot
Instalar Termux:Boot desde la misma fuente que Termux, abrir la app una vez y luego:
```sh
mkdir -p ~/.termux/boot
cp boot-start-market-data.sh ~/.termux/boot/start-market-data.sh
chmod +x ~/.termux/boot/start-market-data.sh
```

Desactivar optimización de batería para Termux y Termux:Boot.
