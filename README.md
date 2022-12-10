# PyMoIP
Python "Modem over IP" for Minitel

Updated 12/2022 :
- Parts of the wiki
- Created Drawio documentation [General connection diagram and data flows]

Updated 08/2021 :
- Gateway code (Current version in PyMoIP/Gateway folder - Previous version (06/2021) in PyMoIP/gateway to be removed)
- Server code (Current version in PyMoIP/Server folder - Previous version (06/2021) in PyMoIP/ServerMode to be removed)

[Creation 07/2020 reviewed 08/2021] Overview

The aim of this project is to try to provide some technical alternatives to VoIP, in order to allow the usage of French Minitel terminals in our modern era, where PSTN technology is disapearing from the entire planet.

As a secondary, but not less essential goal, it allows easily the creation of new videotext Minitel services and contents.

As VoIP seems to be the natural replacement to classical PSTN transport, many drawbacks are observed (mostly related to quality and stability of the V23 link) make think that this solution is not acceptable. Regular FAX transport have been adapted to IP transport with T38 and is now well supported. Regular modem transport have been adapted to IP transport with V150.1 but this approach remains unreachable to normal people due to the ultra high cost of the rare hardware available.

The main idea, inspired by ITU V150.1, is to transport over IP "only the required data" and not "the sound of data". Several usages are to be considerated :

- Acting as a user (calling a WebSocket videotext server) with some real 'old time' hardware :
  - Use any computer/Linux-box (such as a RPi) to initiate a WebSocket session and insure all required translations and adaptations necessary. Many solutions are possible.
      - The Minitel terminal may be directly connected to the Linux-box thru a simple (modified to support 5V TTL) USB-FTDI adapter
      - The Minitel terminal may be indirectly connected to the Linux-box thru a regular USB-Serial adapter and a V23 compatible Hayes modem. This setup requires a minimal phantom PSTN line but might be necessary to allow the usage of Minitel terminals not equiped with peri-informatique connector or ancient computer setups.
        https://github.com/64rulez/PyMoIP/blob/master/LigneFant%C3%B4me.PNG
  
- Acting as a server (provide some videotext contents over WebSockets sessions) :
  - Use any computer/Linux-box (such as a RPi) to accept WebSocket videotext session.
      - Multiple videotext server instances may reside on the same computer.
      - Multiple users may connect to a videotext server instance.
  - Each server instance is independant, with it's own videotext contents and it's own tree
      - Videotext contents might be edited with any legacy or modern tools
      - Tree contents are simple plain text files
      - Dynamically loaded modules might be created in python3
      - A special module "module_teletel" allows to simulate original teletel (3613/3614/3615/etc) operation
        - User redirection to a selected videotext server
        - "Yellow Pages" reference (used by module_teletel) are available there : http://teletel.org/minitel-yp.json
        - (virtual) cost indication on zero line
        - [planned] MGS service

- Acting as a WS/Telnet gateway :
  - Accept WS or Telnet sessions
  - Route session traffic between the user session and a default videotext server
  - Communicate with module_teletel on default videotext server to redirect a user session to an alternative videotext server and recover it once completed
  - [planned] Outgoing sessions to telnet videotext servers (currently, only WS outgoing sessions are supported)

- [Planned] Same hardware setup as when "acting as a user" - needs to find a solution for "virtual ring detection"
    This solution is required to allow simple micro-server BBS setup running on vintage real hardware

- [Planned but out of direct scope of this project] : 
  - A multi-canal VoIP V23 gateway to telnet (or WS ?)
  - A Minitel2 (modem and protocol) simulator to help micro-server BBS setup running on vintage real hardware


[Edit 05/2021 - small review 08/2021] Summary

PyMoIP - aka Python Minitel Over IP

The goal of this project is to propose some technical solutions to allow French Minitel (officially abandonned in 2012) to be usable in our "modern world". This project is currently getting 3 main parts - a 4th one is projected.

Some other project have inspired this - Zigazou's HaMinitel, MiEdit, PyMinitel & CQuest's  

- Part 1 : "User"

This code allows the usage of a legacy Minitel terminal on "modern" WebSocket based servers [As of nowaday, most remaining Minitel servers are WebSocket based]. The main idea beeing to avoid any terminal restrictions (IE : *any* Minitel from the very first prototype to last WebPhones). It supports (at least V23) Hayes compatible modems to permit a direct link to the Web even for terminals without serial port. Historically, after the releases of Minitel 2 & 5, serial ports became not mandatory and 'modernest' terminals had only modems. Without this code, those terminals are only usable over VoIP, what is quite problematic. New version include 8 bits support for photo display [MagisClub/M2 Photo/iTimtel].


- Part 2 : "Server"

This code allow the easy creation of WebSocket based Minitel modular servers. Most of the job is handled by this server code, leaving creativity to build dedicated modules (games, chat, whatever). Videotext page creation might be done nowadays with Zigazou's MiEdit or, in a more rustic way, with logicos's Concept software.


- Part 3 : "Gateway"

This code allows the usage of "legacy" Minitel emulators that were only able to use Telnet protocol, such as iTimtel or Hyperterminal on WebSocket based servers. Additionally, the gateway will try to mimic PAVI/Teletel operation.


- Part 4 : Planned (No name yet - something as "Minitel Modem server") 

A piece of code similar to PyMoIP-User but specific for "legacy" servers. By the ancien times, some peoples used to run Minitel based BBS servers (called in French Micro-serveurs). Those servers where mostly using a minitel as a cheap modem. While this technique was smart by the time, it became very complicated over VoIP and is unreachable from a WebSocket (or telnet) emulator.
