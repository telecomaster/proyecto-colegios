# VHDL Digital Systems - Faculty Knowledge Base
## Module: Synchronous Sequential Circuit Design

### 1. Sensitivity Lists in Synchronous Processes

A sensitivity list defines the signals that trigger the execution of a process.
For a **synchronous process with asynchronous reset**, the sensitivity list must contain ONLY:
- The clock signal (`clk`)
- The asynchronous reset signal (`reset`)

**Incorrect example (causes simulation loops):**
```vhdl
process(clk, reset, count)  -- ERROR: 'count' should NOT be here
```

**Correct example:**
```vhdl
process(clk, reset)  -- CORRECT: only clock and reset
```

Including an output signal like `count` in the sensitivity list of a synchronous process
causes the simulator to re-trigger the process every time `count` changes,
creating an infinite delta-cycle loop and resulting in undefined ('U') states.

---

### 2. Simulation Loop Errors

**Symptom:** Output signal remains in 'U' (undefined) state during simulation.

**Common causes:**
1. Output signal included in sensitivity list (delta-cycle loop)
2. Missing initial value for signals
3. Incomplete reset logic

**Debugging checklist:**
- Verify sensitivity list contains only asynchronous control signals
- Check that all signals have initial values (`:= "0000"`)
- Ensure `rising_edge(clk)` is used for synchronous logic

---

### 3. Standard Synchronous Counter Template

```vhdl
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity simple_counter is
    Port (
        clk   : in  STD_LOGIC;
        reset : in  STD_LOGIC;
        q_out : out STD_LOGIC_VECTOR(3 downto 0)
    );
end simple_counter;

architecture behavioral of simple_counter is
    signal count : unsigned(3 downto 0) := "0000";
begin
    process(clk, reset)  -- CORRECT sensitivity list
    begin
        if reset = '1' then
            count <= "0000";
        elsif rising_edge(clk) then
            count <= count + 1;
        end if;
    end process;

    q_out <= std_logic_vector(count);
end behavioral;
```

---

### 4. Event-Driven Simulation Fundamentals

VHDL simulation operates in discrete time steps called **delta cycles**.
Within a single simulation timestep, multiple delta cycles can occur if signals
keep changing. A process is re-evaluated whenever a signal in its sensitivity
list changes. If a process modifies a signal that is also in its sensitivity list,
it creates a feedback loop across delta cycles, causing simulation to hang or
produce undefined behavior.

**Key rule:** Never include a signal on the LEFT side of a signal assignment (`<=`)
in the sensitivity list of the same process.

---

### 5. VHDL Keywords Reference

| Keyword | Purpose |
|---------|---------|
| `rising_edge(clk)` | Detects positive clock edge |
| `falling_edge(clk)` | Detects negative clock edge |
| `std_logic_vector` | Standard logic bus type |
| `unsigned` | Unsigned arithmetic type |
| `to_integer()` | Converts unsigned to integer |
| `process(...)` | Sequential logic block with sensitivity list |

---

### 6. RF Signal Analysis - Modulation Concepts

**Amplitude Modulation (AM):** The carrier amplitude varies proportionally to the message signal.
Formula: `s(t) = Ac[1 + ka*m(t)]cos(2πfc*t)`

**Frequency Modulation (FM):** The carrier frequency varies proportionally to the message signal.
The bandwidth is determined by Carson's rule: `BT = 2(Δf + fm)`

**Spectrum Analysis:** Use FFT to analyze frequency components. Key parameters:
- Center frequency (fc)
- Bandwidth (BW)
- Signal-to-Noise Ratio (SNR)

---

### 7. Network Protocols - TCP/IP Stack

**TCP Three-Way Handshake:**
1. Client sends SYN packet
2. Server responds with SYN-ACK
3. Client sends ACK

**Routing Protocols:**
- **OSPF:** Link-state, uses Dijkstra algorithm, administrative distance = 110
- **RIP:** Distance-vector, max 15 hops, administrative distance = 120
- **BGP:** Path-vector, used between autonomous systems (AS)

**Key metrics:** Latency, throughput, jitter, packet loss rate
