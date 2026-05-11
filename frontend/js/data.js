const APP_DATA = {
  project: "ATLAS",
  lastUpdated: "11 May 2026, 09:42 AM",

  kpis: {
    totalTickets: 1248,
    resolved: 1089,
    resolutionRate: 87.2,
    slaMet: 92.4,
    activeBreaches: 14,
    csatScore: 4.3,
    avgResolutionHours: 4.2,
    activeEngineers: 38,
    openTickets: 159
  },

  teams: [
    { id:'network',  name:'Network Ops',      lead:'Ravi Kumar',    members:6, open:28, resolved:142, sla:97, domain:'Network',       color:'#E6F1FB', tc:'#0C447C', badge:'#185FA5', desc:'LAN/WAN, VPN, Firewall management' },
    { id:'security', name:'Security',          lead:'Priya Singh',   members:5, open:19, resolved:98,  sla:94, domain:'Security',      color:'#FCEBEB', tc:'#791F1F', badge:'#A32D2D', desc:'Cybersecurity, IAM, Compliance' },
    { id:'hardware', name:'Hardware',           lead:'Deepa Nair',    members:7, open:32, resolved:210, sla:91, domain:'Hardware',      color:'#FAEEDA', tc:'#633806', badge:'#BA7517', desc:'Endpoints, Printers, Asset management' },
    { id:'software', name:'Software',           lead:'Karthik V',     members:6, open:22, resolved:165, sla:89, domain:'Software',      color:'#EAF3DE', tc:'#27500A', badge:'#3B6D11', desc:'Applications, Licenses, OS support' },
    { id:'infra',    name:'Infra & Servers',    lead:'Suresh Babu',   members:5, open:24, resolved:118, sla:78, domain:'Infrastructure',color:'#EEEDFE', tc:'#3C3489', badge:'#534AB7', desc:'Servers, VMware, Cloud infrastructure' },
    { id:'bi',       name:'BI & Analytics',     lead:'Anand Raj',     members:4, open:14, resolved:76,  sla:93, domain:'BI & Analytics',color:'#E1F5EE', tc:'#085041', badge:'#0F6E56', desc:'Power BI, Dashboards, Reporting' },
    { id:'db',       name:'DB & Middleware',    lead:'Meena Pillai',  members:5, open:20, resolved:95,  sla:88, domain:'Database',      color:'#FAECE7', tc:'#712B13', badge:'#993C1D', desc:'SQL, APIs, Middleware integration' }
  ],

  members: {
    network:  [
      {n:'Ravi Kumar',    r:'Lead Engineer',      open:3,  resolved:18, sla:97, av:'RK', wl:'normal'},
      {n:'Arun Selvan',   r:'Network Engineer',   open:5,  resolved:12, sla:95, av:'AS', wl:'normal'},
      {n:'Bharathi M',    r:'L2 Support',         open:4,  resolved:9,  sla:92, av:'BM', wl:'normal'},
      {n:'Chandru P',     r:'L1 Support',         open:6,  resolved:8,  sla:88, av:'CP', wl:'moderate'},
      {n:'Divya R',       r:'Network Engineer',   open:2,  resolved:14, sla:98, av:'DR', wl:'normal'},
      {n:'Elango K',      r:'L2 Support',         open:8,  resolved:7,  sla:82, av:'EK', wl:'high'}
    ],
    security: [
      {n:'Priya Singh',   r:'Security Lead',      open:4,  resolved:15, sla:94, av:'PS', wl:'normal'},
      {n:'Ganesh V',      r:'Security Analyst',   open:5,  resolved:11, sla:91, av:'GV', wl:'moderate'},
      {n:'Harini L',      r:'IAM Specialist',     open:3,  resolved:9,  sla:96, av:'HL', wl:'normal'},
      {n:'Ilango S',      r:'Threat Analyst',     open:4,  resolved:8,  sla:89, av:'IS', wl:'normal'},
      {n:'Jayashree P',   r:'Compliance Analyst', open:3,  resolved:10, sla:93, av:'JP', wl:'normal'}
    ],
    hardware: [
      {n:'Deepa Nair',    r:'Hardware Lead',      open:5,  resolved:22, sla:91, av:'DN', wl:'normal'},
      {n:'Karthi M',      r:'Field Technician',   open:6,  resolved:18, sla:88, av:'KM', wl:'moderate'},
      {n:'Lalitha R',     r:'Asset Manager',      open:4,  resolved:15, sla:93, av:'LR', wl:'normal'},
      {n:'Mani K',        r:'L1 Support',         open:8,  resolved:12, sla:84, av:'MK', wl:'high'},
      {n:'Nithya B',      r:'Field Technician',   open:3,  resolved:19, sla:95, av:'NB', wl:'normal'},
      {n:'Oviya S',       r:'Procurement Lead',   open:2,  resolved:14, sla:97, av:'OS', wl:'normal'},
      {n:'Prasad T',      r:'L2 Support',         open:4,  resolved:16, sla:90, av:'PT', wl:'normal'}
    ],
    software: [
      {n:'Karthik V',     r:'Software Lead',      open:4,  resolved:20, sla:89, av:'KV', wl:'normal'},
      {n:'Ramya D',       r:'App Support',        open:5,  resolved:15, sla:87, av:'RD', wl:'moderate'},
      {n:'Senthil G',     r:'L2 Support',         open:3,  resolved:18, sla:91, av:'SG', wl:'normal'},
      {n:'Thenmozhi K',   r:'License Admin',      open:4,  resolved:12, sla:85, av:'TK', wl:'normal'},
      {n:'Uma P',         r:'App Support',        open:3,  resolved:14, sla:90, av:'UP', wl:'normal'},
      {n:'Vasanth R',     r:'L1 Support',         open:3,  resolved:11, sla:88, av:'VR', wl:'normal'}
    ],
    infra: [
      {n:'Suresh Babu',   r:'Infra Lead',         open:6,  resolved:14, sla:78, av:'SB', wl:'high'},
      {n:'Aarthi N',      r:'Server Admin',       open:5,  resolved:12, sla:80, av:'AN', wl:'moderate'},
      {n:'Balamurugan S', r:'Cloud Ops Engineer', open:4,  resolved:10, sla:82, av:'BS', wl:'normal'},
      {n:'Chithra M',     r:'VMware Specialist',  open:4,  resolved:9,  sla:76, av:'CM', wl:'normal'},
      {n:'Dhanasekar V',  r:'L2 Support',         open:5,  resolved:8,  sla:75, av:'DV', wl:'moderate'}
    ],
    bi: [
      {n:'Anand Raj',     r:'BI Lead',            open:4,  resolved:14, sla:93, av:'AR', wl:'normal'},
      {n:'Eswari K',      r:'Data Analyst',       open:3,  resolved:11, sla:91, av:'EK', wl:'normal'},
      {n:'Fathima Z',     r:'Report Developer',   open:2,  resolved:10, sla:94, av:'FZ', wl:'normal'},
      {n:'Gopinath S',    r:'Tableau Developer',  open:5,  resolved:9,  sla:90, av:'GS', wl:'moderate'}
    ],
    db: [
      {n:'Meena Pillai',  r:'DB Lead',            open:5,  resolved:12, sla:88, av:'MP', wl:'moderate'},
      {n:'Naveen C',      r:'Database Admin',     open:4,  resolved:10, sla:86, av:'NC', wl:'normal'},
      {n:'Pavithra S',    r:'Middleware Engineer',open:3,  resolved:9,  sla:89, av:'PS', wl:'normal'},
      {n:'Rajkumar D',    r:'API Developer',      open:4,  resolved:8,  sla:85, av:'RD', wl:'normal'},
      {n:'Saranya V',     r:'L2 Support',         open:4,  resolved:7,  sla:87, av:'SV', wl:'normal'}
    ]
  },

  tickets: [
    {id:'TK-1248',sub:'VPN connectivity failure in Block-C',team:'Network Ops',teamId:'network',assignee:'Ravi Kumar',priority:'High',status:'In Progress',category:'Network',created:'2026-05-11',updated:'2m ago',desc:'Multiple users in Block-C unable to connect to VPN. Affects ~45 users. Router logs show dropped packets.'},
    {id:'TK-1247',sub:'Email server TLS certificate expiry',team:'Security',teamId:'security',assignee:'Priya Singh',priority:'High',status:'Open',category:'Security',created:'2026-05-11',updated:'18m ago',desc:'TLS certificate on mail.atlas.internal expires in 6 hours. Renewal request raised.'},
    {id:'TK-1246',sub:'Power BI dashboard not loading for finance team',team:'BI & Analytics',teamId:'bi',assignee:'Anand Raj',priority:'Medium',status:'In Progress',category:'BI & Analytics',created:'2026-05-11',updated:'45m ago',desc:'Finance team reports dashboard error: "DataSource not found". Likely gateway issue.'},
    {id:'TK-1245',sub:'Laptop battery replacement — Ref# L2041',team:'Hardware',teamId:'hardware',assignee:'Deepa Nair',priority:'Low',status:'Resolved',category:'Hardware',created:'2026-05-10',updated:'1h ago',desc:'Dell Latitude battery degraded. Replacement part sourced and installed.'},
    {id:'TK-1244',sub:'AD group policy not applying for Dev group',team:'Infra & Servers',teamId:'infra',assignee:'Suresh Babu',priority:'Medium',status:'SLA Breach',category:'Infrastructure',created:'2026-05-10',updated:'2h ago',desc:'Group policy for Developer OU not propagating. Blocked 12 developers from shared drive access.'},
    {id:'TK-1243',sub:'SQL query timeout errors in prod',team:'DB & Middleware',teamId:'db',assignee:'Meena Pillai',priority:'High',status:'In Progress',category:'Database',created:'2026-05-10',updated:'3h ago',desc:'Production DB experiencing timeout on reports queries. Index fragmentation suspected.'},
    {id:'TK-1242',sub:'Antivirus definitions outdated on 20 endpoints',team:'Security',teamId:'security',assignee:'Ganesh V',priority:'Medium',status:'Resolved',category:'Security',created:'2026-05-10',updated:'4h ago',desc:'WSUS push failed for 20 machines. Manually triggered updates on affected endpoints.'},
    {id:'TK-1241',sub:'Office 365 activation failure — new joiners batch',team:'Software',teamId:'software',assignee:'Karthik V',priority:'Medium',status:'Open',category:'Software',created:'2026-05-09',updated:'5h ago',desc:'12 new joiners unable to activate O365 suite. License assignment error in Azure AD.'},
    {id:'TK-1240',sub:'Cisco switch port down on floor 2',team:'Network Ops',teamId:'network',assignee:'Arun Selvan',priority:'High',status:'Resolved',category:'Network',created:'2026-05-09',updated:'6h ago',desc:'Port Gi0/24 on SW-FL2-01 went down. Physical cable replaced and port restored.'},
    {id:'TK-1239',sub:'Projector not detected in Conference Room A',team:'Hardware',teamId:'hardware',assignee:'Karthi M',priority:'Low',status:'Resolved',category:'Hardware',created:'2026-05-09',updated:'7h ago',desc:'HDMI adapter faulty. Replaced with new adapter. Projector now detected.'},
    {id:'TK-1238',sub:'Database replication lag exceeding threshold',team:'DB & Middleware',teamId:'db',assignee:'Naveen C',priority:'High',status:'SLA Breach',category:'Database',created:'2026-05-09',updated:'8h ago',desc:'Replication lag hit 45 min. Secondary DB falling behind primary by 50k transactions.'},
    {id:'TK-1237',sub:'Firewall rule blocking internal API calls',team:'Network Ops',teamId:'network',assignee:'Bharathi M',priority:'High',status:'Open',category:'Network',created:'2026-05-09',updated:'9h ago',desc:'New firewall rule deployed yesterday blocking port 8443 for internal microservices.'},
    {id:'TK-1236',sub:'User account lockout — 5 accounts in HR dept',team:'Security',teamId:'security',assignee:'Harini L',priority:'Medium',status:'Resolved',category:'Security',created:'2026-05-08',updated:'1 day ago',desc:'Password policy sync issue caused repeat lockouts. Resolved via AD attribute reset.'},
    {id:'TK-1235',sub:'VMware ESXi host showing warnings',team:'Infra & Servers',teamId:'infra',assignee:'Chithra M',priority:'Medium',status:'In Progress',category:'Infrastructure',created:'2026-05-08',updated:'1 day ago',desc:'ESXi host esxi-prod-04 reporting memory health warnings. DRS migrated VMs as precaution.'},
    {id:'TK-1234',sub:'Tableau server license expiry alert',team:'BI & Analytics',teamId:'bi',assignee:'Gopinath S',priority:'Medium',status:'Open',category:'BI & Analytics',created:'2026-05-08',updated:'1 day ago',desc:'Tableau Server license expires in 15 days. Renewal requisition sent to procurement.'},
    {id:'TK-1233',sub:'Printer queue stuck on 3rd floor',team:'Hardware',teamId:'hardware',assignee:'Mani K',priority:'Low',status:'SLA Breach',category:'Hardware',created:'2026-05-07',updated:'2 days ago',desc:'HP LaserJet 3rd floor queue stuck with 22 jobs. Spooler service restart required.'},
    {id:'TK-1232',sub:'Cloud storage sync failure for sales team',team:'Infra & Servers',teamId:'infra',assignee:'Balamurugan S',priority:'Medium',status:'In Progress',category:'Infrastructure',created:'2026-05-07',updated:'2 days ago',desc:'OneDrive sync blocked by conditional access policy change. 8 users affected.'},
    {id:'TK-1231',sub:'REST API returning 500 errors intermittently',team:'DB & Middleware',teamId:'db',assignee:'Pavithra S',priority:'High',status:'Open',category:'Database',created:'2026-05-07',updated:'2 days ago',desc:'Payment gateway API throwing 500s every ~30 calls. Middleware logs show DB connection pool exhaustion.'},
    {id:'TK-1230',sub:'Windows 11 upgrade rollout issues',team:'Software',teamId:'software',assignee:'Ramya D',priority:'Medium',status:'Resolved',category:'Software',created:'2026-05-06',updated:'3 days ago',desc:'15 machines failed Win11 upgrade due to TPM check. Resolved by enabling TPM in BIOS.'},
    {id:'TK-1229',sub:'Network bandwidth spike investigation',team:'Network Ops',teamId:'network',assignee:'Divya R',priority:'Medium',status:'Resolved',category:'Network',created:'2026-05-06',updated:'3 days ago',desc:'Unusual 80% bandwidth spike at 2 AM. Traced to backup job misconfiguration. Schedule corrected.'}
  ],

  slaTrend: {
    months: ['Dec 25','Jan 26','Feb 26','Mar 26','Apr 26','May 26'],
    values: [88, 90, 91, 89, 93, 92],
    target: 95
  },

  volumeTrend: {
    days: ['Tue','Wed','Thu','Fri','Sat','Sun','Mon'],
    newTickets:      [42, 38, 55, 47, 29, 33, 48],
    resolvedTickets: [38, 44, 48, 52, 27, 30, 51]
  },

  categoryDist: {
    labels: ['Network','Software','Hardware','Security','BI & Analytics','Database','Infrastructure'],
    values: [28, 22, 18, 15, 8, 12, 17],
    colors: ['#185FA5','#0F6E56','#BA7517','#A32D2D','#0F6E56','#993C1D','#534AB7']
  },

  domainAssignment: {
    'Network':        'Network Ops',
    'Software':       'Software',
    'Hardware':       'Hardware',
    'Security':       'Security',
    'Database':       'DB & Middleware',
    'BI & Analytics': 'BI & Analytics',
    'Infrastructure': 'Infra & Servers'
  },

  ticketCounter: 1249
};
