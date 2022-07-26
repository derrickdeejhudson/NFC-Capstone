# PDHpals-NFC

Technical Report on this NFC Reader - https://derrickdeejhudson.github.io/Personal-Website/Project%20Technical%20Report.pdf


NFC technology provides the fastest way to communicate with two devices within a
fraction of second and is wireless. Using near-field communication (NFC) tags, the wireless
functionality is utilized by storing the virtual identity of a Yu-Gi-Oh! trading card connected to the
cardboard card in physical space. This is achieved by attaching the thin and flexible sticker to a
card sleeve where the card is inserted. The virtual identity is recorded to the NFC chip using
the ndef protocol in the form of a URI link to a digital image of the card in an online database.
Any information beyond a card’s image can be stored and tracked as well. Computers with the
Windows operating system innately have the capacity to detect NFC tags, if connected with an
NFC reader, but do not by default have the capability to execute records stored on NFCs. My
project reads and executes the record stored on the NFC cards in Windows for the intended use
case of streaming and recording videos.
