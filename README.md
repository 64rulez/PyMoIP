# PyMoIP
Python "Modem over IP" for Minitel

The aim of this project is to try to provide some technical alternatives to VoIP, in order to allow the usage of French Minitel terminals in this modern era, where PSTN technology is disapearing from the entire planet.

As VoIP seems to be the natural replacement to classical PSTN transport, many drawbacks are observed (mostly related to quality and stability of the V23 link) make think that this solution is not acceptable. Regular FAX transport have been adapted to IP with T38 and is now well supported. Regular modem transport have been adapted to IP with V150.1 but this approach remains unreachable to normal people due to the ultra high cost of the rare hardware available.

The main idea, inspired by ITU V150.1, is to transport over IP "only the required data" and not "the sound of data". Several usages are to be considerated :
- Acting as a user :
  - Use any Linux-box (such as a RPi) to initiate a WebSocket session and insure all required translations and adaptations
  - The Minitel terminal may be directly connected to the Linux-box thru a simple (modified to support 5V TTL) USB-FTDI adapter
  - The Minitel terminal may be indirectly connected to the Linux-box thru a regular USB-Serial adapter and a V23 compatible Hayes modem. This setup requires a minimal phantom PSTN line but might be necessary to allow the usage of Minitel terminals not equiped with peri-informatique connector.
- Acting as a server :
  - Use any computer to accept WebSocket session
  - Yellow Pages reference (used when acting as a user) are available there : http://teletel.org/minitel-yp.json
  - [Planned] Same hardware setup as when "acting as a user" - needs to find a solution for "virtual ring detection"
    This solution is required to allow simple micro-server BBS setup running on vintage real hardware
    
Current implementation allows only "acting as a user", with both direct and indirect connected Minitel terminal. The WebSocket server might be known in Yellow Pages reference or fully selected at the provided requestor. It needs the use of an updated version of Zigazou's PyMinitel library forked here (https://github.com/64rulez/PyMinitel).


[Edit 05/2021]

PyMoIP - aka Python Minitel Over IP

The goal of this project is to propose some technical solutions to allow French Minitel (officially abandonned in 2012) to be usable in our "modern world". This project is currently getting 3 main parts - a 4th one is projected.

Some other project have inspired this - Zigazou's HaMinitel, MiEdit, PyMinitel & CQuest's  

Summary :
- Part 1 : "User"

This code allows the usage of a legacy Minitel terminal on "modern" WebSocket based servers [As of nowaday, most remaining Minitel servers are WebSocket based]. The main idea beeing to avoid any terminal restrictions (IE : *any* Minitel from the very first prototype to last WebPhones). It supports (at least V23) Hayes compatible modems to permit a direct link to the Web even for terminals without serial port. Historically, after the releases of Minitel 2 & 5, serial ports became not mandatory and 'modernest' terminals had only modems. Without this code, those terminals are only usable over VoIP, what is quite problematic. Newer versions will include 8 bits support for photo display [MagisClub/M2 Photo/iTimtel].


- Part 2 : "Server"

This code allow the easy creation of WebSocket based Minitel modular servers. Most of the job is handled by this server code, leaving creativity to build dedicated modules (games, chat, whatever). Videotext page creation might be done nowadays with Zigazou's MiEdit or, in a more rustic way, with logicos's Concept software.


- Part 3 : "Gateway"

This code allows the usage of "legacy" Minitel emulators that were able to use Telnet protocol, such as iTimtel or Hyperterminal on WebSocket based servers. Additionally, the gateway will try to mimic PAVI operation.


- Part 4 : planned (No name yet - something as "Minitel Modem server") 

A piece of code similar to PyMoIP-User but specific for "legacy" servers. By the ancien times, some peoples used to run Minitel based BBS servers (called in French Micro-serveurs). Those servers where mostly using a minitel as a cheap modem. While this technique was smart by the time, it became very complicated over VoIP and is unreachable from a WebSocket (or telnet) emulator.
