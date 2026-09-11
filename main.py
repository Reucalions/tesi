# Punto di ingresso minimale per eseguire il progetto con «python main.py».
# La logica della CLI vive nel package, così lo script locale, il comando installato
# «thesis-agents» e i test possono utilizzare tutti la stessa funzione main.
from thesis_agents.main import main

# Il blocco si attiva solo eseguendo questo file, non importandolo da un altro modulo.
# SystemExit converte il risultato di main in un codice di uscita per la shell.
if __name__ == "__main__":
    raise SystemExit(main())
