"""
Configuracion de dominios/asignaturas.

Cada dominio es una carpeta dentro de knowledge_base/ (ver knowledge_base/<dominio>/*.md).
Para agregar una asignatura nueva:
  1. Crear la carpeta knowledge_base/<dominio>/ con archivos .md.
  2. Agregar una entrada en DOMAIN_KEYWORDS (palabras/frases que activan el enrutador semantico).
  3. Agregar una entrada en DOMAIN_LABELS (nombre visible para el alumno).
No hace falta tocar router.py ni rag.py.
"""

DOMAIN_KEYWORDS = {
    "vhdl": [
        "vhdl", "verilog", "process sensitivity list", "rising_edge", "falling_edge",
        "std_logic", "std_logic_vector", "vhdl signal", "vhdl entity", "vhdl architecture",
        "behavioral architecture", "synchronous circuit", "flip flop register",
        "vhdl synthesis", "vhdl simulation", "delta cycle simulation",
        "unsigned downto", "port map component", "sequential logic", "combinational logic",
        "setup time hold time", "clock reset counter", "finite state machine vhdl",
        "hardware description language", "digital logic design", "synchronous counter",
        "sensitivity list error", "undefined state simulation", "U state vhdl"
    ],
    "rf": [
        "rf radio frequency", "amplitude modulation", "frequency modulation",
        "spectrum analysis", "antenna design", "signal bandwidth", "carrier wave",
        "noise ratio snr", "fft fourier transform", "decibel power gain",
        "signal attenuation propagation", "wavelength frequency",
        "fm am qam modulation", "ofdm mimo wireless", "beamforming interference",
        "electromagnetic spectrum", "radio wave transmission", "signal processing"
    ],
    "network": [
        "ospf routing protocol", "rip routing protocol", "ospf vs rip",
        "routing protocol comparison", "link state routing", "distance vector routing",
        "tcp ip stack", "network topology", "subnet mask", "bgp autonomous system",
        "ethernet switch router", "firewall vlan", "dhcp dns server",
        "network packet latency", "throughput bandwidth network",
        "osi model layer", "mac address arp", "network protocol",
        "802.1q vlan tagging", "enterprise network", "star topology hub spoke",
        "administrative distance", "convergence routing", "network scalability"
    ]
}

DOMAIN_LABELS = {
    "vhdl": "Agente VHDL/Verilog",
    "rf": "Agente de Señales RF",
    "network": "Agente de Redes"
}
