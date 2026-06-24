/*
 * SchoolPortaal - Geoptimaliseerde C++ Webserver
 * Compileer: g++ -O2 -o server.exe Main.cpp -lws2_32 -std=c++17
 * Start:     server.exe
 * Open:      http://localhost:8080
 */
#define _WINSOCK_DEPRECATED_NO_WARNINGS
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <string>
#include <map>
#include <vector>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <ctime>
#include <random>
#pragma comment(lib, "ws2_32.lib")

// ================== STATISCHE HTML BROKKEN ==================
const char* HDR1 = "<!DOCTYPE html><html lang=\"nl\"><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\"><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);min-height:100vh;color:#fff}.navbar{background:rgba(0,0,0,.3);backdrop-filter:blur(10px);padding:15px 40px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,.1)}.navbar .logo{font-size:24px;font-weight:bold;color:#7c4dff}.navbar a{color:#ccc;text-decoration:none;margin-left:20px;padding:8px 16px;border-radius:6px}.navbar a:hover{background:rgba(124,77,255,.3);color:#fff}.btn-ug{background:#ff5252;color:#fff;border:none;padding:8px 20px;border-radius:6px;cursor:pointer}.container{max-width:1200px;margin:0 auto;padding:40px 20px}.card{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:30px;margin-bottom:20px}.card h2{color:#b388ff;margin-bottom:15px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}.stat-card{background:rgba(124,77,255,.15);border:1px solid rgba(124,77,255,.3);border-radius:12px;padding:25px;text-align:center}.stat-card .getal{font-size:48px;font-weight:bold;color:#b388ff}.stat-card .label{font-size:14px;color:#aaa}table{width:100%;border-collapse:collapse;margin-top:15px}th,td{padding:12px;text-align:left;border-bottom:1px solid rgba(255,255,255,.1)}th{color:#b388ff}tr:hover{background:rgba(255,255,255,.05)}.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold}.badge-goed{background:rgba(76,175,80,.3);color:#69f0ae}.badge-niet-goed{background:rgba(255,82,82,.3);color:#ff8a80}.badge-bezig{background:rgba(255,214,0,.3);color:#ffd740}.btn{display:inline-block;padding:10px 24px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:600;border:none;cursor:pointer}.btn-p{background:#7c4dff;color:#fff}.btn-d{background:#ff5252;color:#fff}.welkom{font-size:20px;color:#ccc;margin-bottom:30px}.welkom strong{color:#b388ff}input,select,textarea{width:100%;padding:10px 14px;border:1px solid rgba(255,255,255,.2);border-radius:8px;background:rgba(255,255,255,.05);color:#fff;font-size:14px;outline:none;margin-top:4px}label.f{display:block;margin-bottom:12px;color:#b388ff;font-weight:600}.rol-knop{display:block;text-align:center;padding:15px;background:rgba(124,77,255,.1);border:2px solid rgba(124,77,255,.3);border-radius:10px;cursor:pointer;transition:.2s}.rol-knop:hover{background:rgba(124,77,255,.25)}.rol-knop.actief{background:rgba(124,77,255,.4);border-color:#b388ff;box-shadow:0 0 15px rgba(124,77,255,.4)}.antw-blok{display:block;width:100%;padding:20px;margin-bottom:12px;background:rgba(255,255,255,.05);border:2px solid rgba(255,255,255,.1);border-radius:12px;cursor:pointer;font-size:18px;text-align:left;transition:.15s}.antw-blok:hover{background:rgba(124,77,255,.2);border-color:rgba(124,77,255,.5)}.antw-blok input[type=radio]{display:none}.antw-blok:has(input:checked){background:rgba(124,77,255,.35);border-color:#7c4dff;box-shadow:0 0 10px rgba(124,77,255,.3)}.antw-blok .letter{display:inline-block;font-weight:bold;color:#b388ff;font-size:22px;margin-right:15px;min-width:35px}</style></head>";

const char* NAV_START = "<nav class=\"navbar\"><span class=\"logo\">SchoolPortaal</span><div><a href=\"/";
const char* NAV_END_D = "\">Dashboard</a><a href=\"/docent/klassen\">Klassen</a><a href=\"/docent/toetsen\">Toetsen</a><a href=\"/docent/quizzen\">Quizzen</a><a href=\"/docent/cijfers\">Cijfers</a><a href=\"/docent/leerlingen\">Leerlingen</a>";
const char* NAV_END_L = "\">Dashboard</a><a href=\"/leerling/cijfers\">Mijn Cijfers</a><a href=\"/leerling/quizzen\">Quizzen</a><a href=\"/leerling/schoolgids\">Schoolgids</a>";
const char* NAV_TAIL = "<span style=\"color:#b388ff;margin-left:20px;\">";
const char* NAV_UG = "</span><a href=\"/uitloggen\" class=\"btn-ug\">Uitloggen</a></div></nav>";

struct Gebruiker {
    std::string gebruikersnaam, wachtwoord, naam, rol, klas, vak;
};

struct Toets {
    std::string titel, vak, klas, datum, tijd, beschrijving;
    int duur;
    std::string aangemaakt_door;
};

std::vector<Toets> toetsen;

struct Vraag {
    std::string tekst;
    std::string opties[4];
    int antwoord;
};

struct Quiz {
    std::string titel, vak, klas, beschrijving, aangemaakt_door;
    std::vector<Vraag> vragen;
};

std::vector<Quiz> quizzen;

struct ActieveQuiz {
    std::string pin;
    int quizIndex;
    std::string status; // "wacht", "actief", "klaar"
    int huidigeVraag;
    std::map<std::string, int> spelers; // naam -> score
    std::map<std::string, int> antwoorden; // naam -> gekozen antwoord (voor huidige vraag)
    time_t startTijd;
};

std::vector<ActieveQuiz> actieveQuizzen;

std::string genereerPin() {
    static const char cijfers[] = "0123456789";
    std::string pin;
    static int teller = 1000;
    pin = std::to_string(teller++);
    if (teller > 9999) teller = 1000;
    return pin;
}

ActieveQuiz* vindActieveQuiz(const std::string& pin) {
    for (auto& aq : actieveQuizzen) {
        if (aq.pin == pin) return &aq;
    }
    return nullptr;
}

// ================== DATABASE ==================
class GebruikersDatabase {
    std::vector<Gebruiker> gebruikers;
public:
    Gebruiker* vind(const std::string& un, const std::string& ww) {
        for (auto& g : gebruikers) if (g.gebruikersnaam == un && g.wachtwoord == ww) return &g;
        return nullptr;
    }
    GebruikersDatabase() {
        gebruikers.reserve(70);
        gebruikers.push_back({"maartsen","maa123","Mevr. M. van Aartsen","docent","","ak"});
        gebruikers.push_back({"ialbracht","abt123","Mevr. I. Albracht","docent","","fa"});
        gebruikers.push_back({"baltelaar","alt123","Mevr. B. Altelaar","docent","","na"});
        gebruikers.push_back({"fbeer","bee123","Mevr. F. de Beer","docent","","bv"});
        gebruikers.push_back({"bberends","beb123","Mevr. ir. B. Berends","docent","","na"});
        gebruikers.push_back({"hbosman","bmn123","Dhr. H. Bosman","docent","","mu"});
        gebruikers.push_back({"gbossink","bog123","Mevr. G. Bossink","docent","","du"});
        gebruikers.push_back({"jbrouwer","bro123","Dhr. drs. J.J. Brouwer","docent","","fa/la"});
        gebruikers.push_back({"rdekker","dkr123","Dhr. R.D. Dekker MEd","docent","","na/sk"});
        gebruikers.push_back({"ydijk","dyk123","Mevr. drs. J.Y.N. van Dijk","docent","","bi"});
        gebruikers.push_back({"mdijken","dkn123","Mevr. M. v. Dijken","docent","","lo"});
        gebruikers.push_back({"adrost","dst123","Dhr. A. Drost","docent","","gd"});
        gebruikers.push_back({"nflier","flb123","Mevr. N. Flier","docent","","wi"});
        gebruikers.push_back({"bflierhaar","flh123","Mevr. B. te Flierhaar","docent","","en"});
        gebruikers.push_back({"cgelder","gen123","Mevr. A.C. van Gelder","docent","","gs"});
        gebruikers.push_back({"mgoede","gom123","Mevr. M. de Goede","docent","","fa"});
        gebruikers.push_back({"lhalsema","hal123","Mevr. L. van Halsema MA","docent","","ne"});
        gebruikers.push_back({"whave","haw123","Dhr. W.H. ten Have MEd","docent","","en"});
        gebruikers.push_back({"mhazenberg","hzb123","Mevr. M. Hazenberg","docent","","fa"});
        gebruikers.push_back({"ehof","hoa123","Dhr. E.E. van 't Hof","docent","","ak"});
        gebruikers.push_back({"mhuijssoon","hum123","Mevr. M. Huijssoon","docent","","nlt/na"});
        gebruikers.push_back({"thhul","hul123","Dhr. D.T. van 't Hul","docent","","wi"});
        gebruikers.push_back({"khuls","hls123","Mevr. K.G. Huls","docent","","gs"});
        gebruikers.push_back({"akazemier","kaz123","Dhr. A.W.J. Kazemier","docent","","lo"});
        gebruikers.push_back({"akeijl","kei123","Mevr. A.J. Keijl SEN","docent","","ne"});
        gebruikers.push_back({"rknol","knl123","Dhr. R. Knol","docent","","ak"});
        gebruikers.push_back({"rknoll","kll123","Dhr. R. Knoll","docent","","ec/be"});
        gebruikers.push_back({"hkodde","kod123","Mevr. H. Kodde","docent","","wi"});
        gebruikers.push_back({"jekooistra","koi123","Mevr. J. Kooistra","docent","","ckv"});
        gebruikers.push_back({"aleusink","lea123","Mevr. A. Leusink","docent","","du"});
        gebruikers.push_back({"gleusink","lsk123","Mevr. G. Leusink","docent","","wi"});
        gebruikers.push_back({"cmerema","mec123","Mevr. C.P. Merema MA","docent","","ne"});
        gebruikers.push_back({"mnitrauw","nit123","Mevr. M. Nitrauw","docent","","du"});
        gebruikers.push_back({"bpol","pob123","Dhr. B. Pol","docent","","ma"});
        gebruikers.push_back({"tpol","plt123","Mevr. T. van de Pol","docent","","du"});
        gebruikers.push_back({"alpolinder","poi123","Mevr. A. Polinder","docent","","bi"});
        gebruikers.push_back({"dpoppe","pop123","Dhr. D.J. van de Poppe","docent","","na"});
        gebruikers.push_back({"mpost","pst123","Dhr. J.M. Post","docent","","gs/ma"});
        gebruikers.push_back({"mputten","ptn123","Mevr. M. van Putten","docent","","bio"});
        gebruikers.push_back({"ereinders","res123","Mevr. E. Reinders","docent","","wi"});
        gebruikers.push_back({"rrubura","rub123","Mevr. R. Rubura","docent","","en"});
        gebruikers.push_back({"eschaftenaar","sfn123","Mevr. drs. E.M. Schaftenaar MEd","docent","","ne"});
        gebruikers.push_back({"fschekman","skm123","Mevr. F. Schekman","docent","","ne"});
        gebruikers.push_back({"jschoonhoven","scn123","Mevr. J. Schoonhoven","docent","","bv"});
        gebruikers.push_back({"gschreurs","srs123","Dhr. G. Schreurs","docent","","lo"});
        gebruikers.push_back({"mselles","ses123","Mevr. M. Selles","docent","","en"});
        gebruikers.push_back({"psiebering","sie123","Dhr. P. Siebering","docent","","ec/be"});
        gebruikers.push_back({"wsollie","sol123","Dhr. W.J. Sollie","docent","","bi"});
        gebruikers.push_back({"bspijkerboer","spb123","Dhr. B.J. Spijkerboer","docent","","gd"});
        gebruikers.push_back({"cspijkerboer","spi123","Dhr. C. Spijkerboer MEd","docent","","bi"});
        gebruikers.push_back({"nstouwe","stw123","Mevr. N. van der Stouwe","docent","","ne"});
        gebruikers.push_back({"dtang","tan123","Dhr. D. Tang","docent","","wi"});
        gebruikers.push_back({"eterlouw","tee123","Mevr. E.P.C.P. Terlouw","docent","","bv/ckv"});
        gebruikers.push_back({"mverspuij","vpu123","Mevr. M. Verspuij","docent","","en"});
        gebruikers.push_back({"mvries","vrm123","Dhr. M. de Vries","docent","","ne"});
        gebruikers.push_back({"wwaard","waa123","Dhr. W. de Waard","docent","","lo"});
        gebruikers.push_back({"awendt","wdt123","Dhr. A. Wendt","docent","","ec/be"});
        gebruikers.push_back({"dwesterink","wsk123","Mevr. D. Westerink","docent","","en"});
        gebruikers.push_back({"bwillemsen","wls123","Dhr. T.A. Willemsen","docent","","sk"});
        gebruikers.push_back({"jwinters","win123","Mevr. J.S.E. Winters","docent","","ec"});
        gebruikers.push_back({"jzijlstra","zis123","Dhr. drs. J.J. Zijlstra","docent","","gd"});
        gebruikers.push_back({"czwart","zwt123","Mevr. C. de Zwart","docent","","en"});
        gebruikers.push_back({"piet","leerling123","Piet de Groot","leerling","4VWO",""});
        gebruikers.push_back({"anna","leerling123","Anna Smit","leerling","3HAVO",""});
        gebruikers.push_back({"tom","leerling123","Tom Visser","leerling","5VWO",""});
        gebruikers.push_back({"lisa","leerling123","Lisa Bakker","leerling","2HAVO",""});
    }
};

struct Sessie {
    std::string gebruikersnaam, rol, naam, klas, vak;
    time_t aangemaakt;
};

class SessieBeheerder {
    std::map<std::string, Sessie> sessies;
    int teller = 0;
public:
    std::string maakSessie(const Gebruiker& g) {
        std::string id; id.resize(32);
        static const char t[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        std::mt19937 rng(++teller + (unsigned int)time(nullptr));
        std::uniform_int_distribution<> d(0, sizeof(t)-2);
        for (int i=0; i<32; i++) id[i] = t[d(rng)];
        sessies[id] = {g.gebruikersnaam, g.rol, g.naam, g.klas, g.vak, time(nullptr)};
        return id;
    }
    Sessie* haalOp(const std::string& id) {
        auto it = sessies.find(id);
        if (it != sessies.end() && time(nullptr) - it->second.aangemaakt < 86400) return &it->second;
        if (it != sessies.end()) sessies.erase(it);
        return nullptr;
    }
    void verwijder(const std::string& id) { sessies.erase(id); }
};

// ================== HELPER FUNCTIES ==================
std::string postWaarde(const std::string& b, const std::string& v) {
    size_t p = b.find(v+"="); if (p==std::string::npos) return "";
    size_t s = p+v.length()+1, e = b.find("&", s); if (e==std::string::npos) e=b.length();
    std::string w = b.substr(s, e-s);
    std::string d; d.reserve(w.length());
    for (size_t i=0; i<w.length(); i++) {
        if (w[i]=='+') d+=' ';
        else if (w[i]=='%' && i+2<w.length()) { int h; std::istringstream iss(w.substr(i+1,2)); if(iss>>std::hex>>h){d+=(char)h;i+=2;} else d+=w[i]; }
        else d+=w[i];
    }
    return d;
}

std::string haalCookie(const std::string& r, const std::string& n) {
    size_t p = r.find("Cookie: "); if (p==std::string::npos) return "";
    size_t e = r.find("\r\n", p); if (e==std::string::npos) e=r.length();
    std::string s = r.substr(p+8, e-p-8);
    size_t cp = s.find(n+"="); if (cp==std::string::npos) return "";
    cp += n.length()+1;
    size_t ce = s.find(";", cp);
    return s.substr(cp, ce==std::string::npos ? std::string::npos : ce-cp);
}

// ================== NAV + PAGINA BOUWERS ==================
void nav(std::stringstream& ss, const std::string& rol, const std::string& naam) {
    ss << NAV_START;
    if (rol == "docent") ss << "docent\">Dashboard" << NAV_END_D;
    else ss << "leerling\">Dashboard" << NAV_END_L;
    ss << NAV_TAIL << naam << " (" << (rol=="docent"?"Docent":"Leerling") << ")" << NAV_UG;
}

std::string inlogPagina(const std::string& fout="") {
    std::stringstream ss;
    ss << HDR1 << "<title>Inloggen - SchoolPortaal</title></head><body><div style=\"display:flex;justify-content:center;align-items:center;min-height:100vh\"><div style=\"width:100%;max-width:450px;padding:20px\">"
    "<div style=\"text-align:center;margin-bottom:40px\"><h1 style=\"font-size:36px;color:#b388ff;margin-bottom:8px\">SchoolPortaal</h1><p style=\"color:#888\">Log in</p></div>";
    if (!fout.empty()) ss << "<div style=\"background:rgba(255,82,82,.2);border:1px solid #ff5252;border-radius:8px;padding:12px;margin-bottom:20px;color:#ff8a80;text-align:center\">" << fout << "</div>";
    ss << "<div class=\"card\"><form method=\"POST\" action=\"/inloggen\">"
    "<label class=\"f\">Rol<div style=\"display:flex;gap:10px\">"
    "<label class=\"rol-knop\"><input type=\"radio\" name=\"rol\" value=\"docent\" onchange=\"this.parentElement.classList.toggle('actief',this.checked)\" style=\"display:none\"> Docent</label>"
    "<label class=\"rol-knop\"><input type=\"radio\" name=\"rol\" value=\"leerling\" onchange=\"this.parentElement.classList.toggle('actief',this.checked)\" style=\"display:none\"> Leerling</label>"
    "</div></label>"
    "<label class=\"f\">Gebruikersnaam<input type=\"text\" name=\"gebruikersnaam\" placeholder=\"Gebruikersnaam\" required></label>"
    "<label class=\"f\">Wachtwoord<input type=\"password\" name=\"wachtwoord\" placeholder=\"Wachtwoord\" required></label>"
    "<button type=\"submit\" class=\"btn btn-p\" style=\"width:100%;padding:14px;font-size:16px\">Inloggen</button>"
    "</form></div></div></div></body></html>";
    return ss.str();
}

void maakDashboard(std::stringstream& ss, const std::string& naam, const std::string& info, const std::string& rol) {
    ss << HDR1 << "<title>Dashboard</title></head><body>";
    nav(ss, rol, naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Welkom terug, <strong>" << naam << "</strong>! | " << info << "</div>"
    "<div class=\"grid\"><div class=\"stat-card\"><div class=\"getal\">47</div><div class=\"label\">Leerlingen</div></div>"
    "<div class=\"stat-card\"><div class=\"getal\">" << toetsen.size()+quizzen.size() << "</div><div class=\"label\">Items</div></div>"
    "<div class=\"stat-card\"><div class=\"getal\">5</div><div class=\"label\">Cijfers</div></div></div></div></body></html>";
}

void maakCijfers(std::stringstream& ss, const std::string& naam, const std::string& vak) {
    ss << HDR1 << "<title>Cijfers</title></head><body>"; nav(ss,"docent",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Cijfers - <strong>" << vak << "</strong></div>"
    "<div class=\"card\"><h2>Cijferoverzicht</h2><table><tr><th>Leerling</th><th>Klas</th><th>Cijfer</th><th>Type</th></tr>"
    "<tr><td>Piet de Groot</td><td>4VWO</td><td style=\"color:#69f0ae\">8.5</td><td>Proefwerk</td></tr>"
    "<tr><td>Anna Smit</td><td>3HAVO</td><td style=\"color:#69f0ae\">7.2</td><td>Huiswerk</td></tr>"
    "<tr><td>Tom Visser</td><td>5VWO</td><td style=\"color:#ffd740\">6.0</td><td>Toets</td></tr></table></div></div></body></html>";
}

void maakKlassen(std::stringstream& ss, const std::string& naam) {
    ss << HDR1 << "<title>Klassen</title></head><body>"; nav(ss,"docent",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Overzicht <strong>Klassen</strong></div>";
    const char* jaren[] = {"2","3","4","5","6"};
    for (auto& j : jaren) {
        ss << "<div class=\"card\"><h2>Klas " << j << "</h2><div class=\"grid\">"
        "<div class=\"stat-card\"><div class=\"getal\" style=\"font-size:28px\">la" << j << "1</div><div class=\"label\">La</div></div>"
        "<div class=\"stat-card\"><div class=\"getal\" style=\"font-size:28px\">la" << j << "2</div><div class=\"label\">La</div></div>"
        "<div class=\"stat-card\"><div class=\"getal\" style=\"font-size:28px\">lh" << j << "1</div><div class=\"label\">Lh</div></div>"
        "<div class=\"stat-card\"><div class=\"getal\" style=\"font-size:28px\">lh" << j << "2</div><div class=\"label\">Lh</div></div>";
        if (j[0]!='6') ss << "<div class=\"stat-card\"><div class=\"getal\" style=\"font-size:28px\">lh" << j << "3</div><div class=\"label\">Lh</div></div>";
        ss << "</div></div>";
    }
    ss << "</div></body></html>";
}

void maakLeerlingen(std::stringstream& ss, const std::string& naam) {
    ss << HDR1 << "<title>Leerlingen</title></head><body>"; nav(ss,"docent",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Overzicht <strong>Leerlingen</strong></div>"
    "<div class=\"card\"><h2>Alle Leerlingen</h2><table><tr><th>Naam</th><th>Klas</th><th>Gemiddelde</th><th>Status</th></tr>"
    "<tr><td>Piet</td><td>4VWO</td><td style=\"color:#69f0ae\">7.6</td><td><span class=\"badge badge-goed\">Actief</span></td></tr>"
    "<tr><td>Anna</td><td>3HAVO</td><td style=\"color:#69f0ae\">7.1</td><td><span class=\"badge badge-goed\">Actief</span></td></tr>"
    "<tr><td>Tom</td><td>5VWO</td><td style=\"color:#ffd740\">6.2</td><td><span class=\"badge badge-bezig\">Bezig</span></td></tr>"
    "<tr><td>Lisa</td><td>2HAVO</td><td style=\"color:#ff8a80\">5.4</td><td><span class=\"badge badge-niet-goed\">Ingeschreven</span></td></tr></table></div></div></body></html>";
}

void maakLkCijfers(std::stringstream& ss, const std::string& naam, const std::string& klas) {
    ss << HDR1 << "<title>Mijn Cijfers</title></head><body>"; nav(ss,"leerling",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Cijfers van <strong>" << naam << "</strong></div>"
    "<div class=\"card\"><h2>Overzicht</h2><h3>Wiskunde</h3><table><tr><th>Type</th><th>Cijfer</th><th>%</th></tr>"
    "<tr><td>Proefwerk</td><td style=\"color:#69f0ae\">8.5</td><td>40%</td></tr>"
    "<tr><td>Huiswerk</td><td style=\"color:#69f0ae\">7.8</td><td>20%</td></tr></table>"
    "<h3>Nederlands</h3><table><tr><th>Type</th><th>Cijfer</th><th>%</th></tr>"
    "<tr><td>Huiswerk</td><td style=\"color:#69f0ae\">7.2</td><td>30%</td></tr>"
    "<tr><td>Tentamen</td><td style=\"color:#ffd740\">6.0</td><td>35%</td></tr></table></div></div></body></html>";
}

// ================== TOETSEN PAGINA ==================
void maakToetsen(std::stringstream& ss, const std::string& naam, const std::string& vak) {
    ss << HDR1 << "<title>Toetsen</title></head><body>"; nav(ss,"docent",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Toetsen - <strong>" << vak << "</strong></div>"
    "<div class=\"card\"><h2>Nieuwe Toets</h2><form method=\"POST\" action=\"/docent/toetsen\">"
    "<div style=\"display:grid;grid-template-columns:1fr 1fr;gap:15px\">"
    "<label class=\"f\">Titel<input type=\"text\" name=\"titel\" required></label>"
    "<label class=\"f\">Vak<select name=\"vak\"><option>ak</option><option>fa</option><option>na</option><option>bv</option><option>wi</option><option>en</option><option>gs</option><option>ne</option><option>bi</option><option>ma</option><option>du</option><option>ec</option><option>sk</option></select></label>"
    "<label class=\"f\">Klas<select name=\"klas\"><option>la21</option><option>la22</option><option>lh21</option><option>lh22</option><option>lh23</option><option>la31</option><option>la32</option><option>lh31</option><option>lh32</option><option>lh33</option><option>la41</option><option>la42</option><option>lh41</option><option>lh42</option><option>lh43</option><option>la51</option><option>la52</option><option>lh51</option><option>lh52</option><option>lh53</option><option>la61</option><option>lh61</option><option>lh62</option></select></label>"
    "<label class=\"f\">Datum<input type=\"date\" name=\"datum\" required></label>"
    "<label class=\"f\">Tijd<input type=\"time\" name=\"tijd\" required></label>"
    "<label class=\"f\">Duur<input type=\"number\" name=\"duur\" value=\"60\" min=\"5\" max=\"300\"></label></div>"
    "<button type=\"submit\" class=\"btn btn-p\" style=\"margin-top:10px\">Aanmaken</button></form></div>"
    "<div class=\"card\"><h2>Toetsen (" << toetsen.size() << ")</h2><table><tr><th>Titel</th><th>Vak</th><th>Klas</th><th>Datum</th><th>Actie</th></tr>";
    if (toetsen.empty()) ss << "<tr><td colspan=\"5\" style=\"text-align:center;color:#888\">Geen toetsen</td></tr>";
    else for (int i=0; i<(int)toetsen.size(); i++) {
        auto& t = toetsen[i];
        ss << "<tr><td>" << t.titel << "</td><td>" << t.vak << "</td><td>" << t.klas << "</td><td>" << t.datum << " " << t.tijd << "</td>"
        "<td><form method=\"POST\" action=\"/docent/toetsen/verwijder\" style=\"display:inline\"><input type=\"hidden\" name=\"index\" value=\"" << i << "\">"
        "<button type=\"submit\" class=\"btn btn-d\" style=\"padding:4px 12px\">Del</button></form></td></tr>";
    }
    ss << "</table></div></div></body></html>";
}

// ================== QUIZ PAGINA'S ==================
void maakQuizOverzicht(std::stringstream& ss, const std::string& naam, const std::string& extra) {
    ss << HDR1 << "<title>Quizzen</title></head><body>"; nav(ss,"docent",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Quizzen - <strong>" << extra << "</strong></div>"
    "<div class=\"card\"><h2>Nieuwe Quiz</h2><form method=\"POST\" action=\"/docent/quizzen\">"
    "<div style=\"display:grid;grid-template-columns:1fr 1fr;gap:15px\">"
    "<label class=\"f\">Titel<input type=\"text\" name=\"titel\" required></label>"
    "<label class=\"f\">Vak<select name=\"vak\"><option>ak</option><option>fa</option><option>na</option><option>bv</option><option>wi</option><option>en</option><option>gs</option><option>ne</option><option>bi</option><option>ma</option></select></label>"
    "<label class=\"f\">Klas<select name=\"klas\"><option>la21</option><option>la22</option><option>lh21</option><option>lh22</option><option>lh23</option><option>la31</option><option>la32</option><option>lh31</option><option>lh32</option><option>lh33</option><option>la41</option><option>la42</option><option>lh41</option><option>lh42</option><option>lh43</option><option>la51</option><option>la52</option><option>lh51</option><option>lh52</option><option>lh53</option><option>la61</option><option>lh61</option><option>lh62</option></select></label></div>"
    "<button type=\"submit\" class=\"btn btn-p\">Aanmaken</button></form></div>"
    "<div class=\"card\"><h2>Quizzen (" << quizzen.size() << ")</h2><table><tr><th>Titel</th><th>Vak</th><th>Klas</th><th>Vragen</th><th>Actie</th></tr>";
    if (quizzen.empty()) ss << "<tr><td colspan=\"5\" style=\"text-align:center;color:#888\">Geen quizzen</td></tr>";
    else for (int i=0; i<(int)quizzen.size(); i++) {
        auto& q = quizzen[i];
        ss << "<tr><td>" << q.titel << "</td><td>" << q.vak << "</td><td>" << q.klas << "</td><td>" << q.vragen.size() << "</td>"
        "<td><a href=\"/docent/quiz/" << i << "\" class=\"btn btn-p\" style=\"padding:4px 12px\">Vragen</a> "
        "<form method=\"POST\" action=\"/docent/quizzen/verwijder\" style=\"display:inline\"><input type=\"hidden\" name=\"index\" value=\"" << i << "\">"
        "<button type=\"submit\" class=\"btn btn-d\" style=\"padding:4px 12px\">Del</button></form></td></tr>";
    }
    ss << "</table></div></div></body></html>";
}

void maakQuizDetail(std::stringstream& ss, const std::string& naam, int idx) {
    if (idx<0 || idx>=(int)quizzen.size()) { ss << HDR1 << "<title>Fout</title></head><body>"; nav(ss,"docent",naam); ss << "<div class=\"container\"><div class=\"card\"><h2>Niet gevonden</h2></div></div></body></html>"; return; }
    auto& q = quizzen[idx];
    ss << HDR1 << "<title>" << q.titel << "</title></head><body>"; nav(ss,"docent",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Quiz: <strong>" << q.titel << "</strong> | " << q.vak << " | " << q.klas << "</div>"
    "<div class=\"card\"><h2>Vragen (" << q.vragen.size() << ")</h2>";
    for (int i=0; i<(int)q.vragen.size(); i++) {
        auto& v = q.vragen[i];
        ss << "<div style=\"background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:15px;margin-bottom:10px\">"
        "<p><strong>Vraag " << i+1 << ":</strong> " << v.tekst << "</p><p style=\"margin-top:5px\">";
        for (int o=0; o<4; o++) ss << "<span style=\"" << (o==v.antwoord?"color:#69f0ae;font-weight:bold":"color:#ccc") << ";margin-right:15px\">" << char('A'+o) << ". " << v.opties[o] << "</span>";
        ss << "</p></div>";
    }
    ss << "</div>"
    "<div class=\"card\"><h2>Nieuwe Vraag</h2><form method=\"POST\" action=\"/docent/quiz/" << idx << "/vraag\">"
    "<label class=\"f\">Vraag<textarea name=\"vraag\" rows=\"2\" required style=\"resize:vertical\"></textarea></label>"
    "<div style=\"display:grid;grid-template-columns:1fr 1fr;gap:10px\">"
    "<label class=\"f\">A<input type=\"text\" name=\"opt0\" required></label>"
    "<label class=\"f\">B<input type=\"text\" name=\"opt1\" required></label>"
    "<label class=\"f\">C<input type=\"text\" name=\"opt2\" required></label>"
    "<label class=\"f\">D<input type=\"text\" name=\"opt3\" required></label></div>"
    "<label class=\"f\">Correct<select name=\"antwoord\"><option value=\"0\">A</option><option value=\"1\">B</option><option value=\"2\">C</option><option value=\"3\">D</option></select></label>"
    "<button type=\"submit\" class=\"btn btn-p\">Toevoegen</button></form></div>"
    "<a href=\"/docent/quizzen\" class=\"btn btn-d\">Terug</a></div></body></html>";
}

void maakLkQuizzen(std::stringstream& ss, const std::string& naam) {
    ss << HDR1 << "<title>Quizzen</title></head><body>"; nav(ss,"leerling",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Beschikbare <strong>Quizzen</strong></div>";
    if (quizzen.empty()) ss << "<div class=\"card\"><p style=\"text-align:center;color:#888\">Geen quizzen beschikbaar.</p></div>";
    else for (int i=0; i<(int)quizzen.size(); i++) {
        auto& q = quizzen[i];
        ss << "<div class=\"card\"><h2>" << q.titel << "</h2><p><strong>Vak:</strong> " << q.vak << " | <strong>Klas:</strong> " << q.klas << " | <strong>Vragen:</strong> " << q.vragen.size() << "</p>"
        << (q.beschrijving.empty()?"":"<p style=\"color:#888;margin-top:8px\">"+q.beschrijving+"</p>")
        << "<a href=\"/leerling/quiz/" << i << "\" class=\"btn btn-p\" style=\"margin-top:15px\">Quiz Maken</a></div>";
    }
    ss << "</div></body></html>";
}

void maakLkQuizMaken(std::stringstream& ss, const std::string& naam, int idx) {
    if (idx<0 || idx>=(int)quizzen.size()) return;
    auto& q = quizzen[idx];
    ss << HDR1 << "<title>" << q.titel << "</title></head><body>";
    nav(ss,"leerling",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">" << q.titel << " | " << q.vak << "</div><form method=\"POST\" action=\"/leerling/quiz/" << idx << "/antwoord\">";
    for (int i=0; i<(int)q.vragen.size(); i++) {
        auto& v = q.vragen[i];
        ss << "<div style=\"background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:20px;margin-bottom:15px\">"
        "<p style=\"font-size:16px;margin-bottom:12px\"><strong>Vraag " << i+1 << ":</strong> " << v.tekst << "</p>";
        for (int o=0; o<4; o++) ss << "<label style=\"display:block;padding:8px 12px;margin-bottom:5px;background:rgba(124,77,255,.1);border:1px solid rgba(124,77,255,.2);border-radius:6px;cursor:pointer\">"
        "<input type=\"radio\" name=\"vraag" << i << "\" value=\"" << o << "\" required> " << char('A'+o) << ". " << v.opties[o] << "</label>";
        ss << "</div>";
    }
    ss << "<button type=\"submit\" class=\"btn btn-p\" style=\"padding:14px 30px;font-size:16px\">Inleveren</button></form></div></body></html>";
}

void maakLkQuizResultaat(std::stringstream& ss, const std::string& naam, int idx, const std::string& pb) {
    if (idx<0 || idx>=(int)quizzen.size()) return;
    auto& q = quizzen[idx]; int goed=0, tot=(int)q.vragen.size();
    ss << HDR1 << "<title>Resultaat</title></head><body>"; nav(ss,"leerling",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Resultaat: <strong>" << q.titel << "</strong></div>";
    for (int i=0; i<tot; i++) {
        std::string antw = postWaarde(pb, "vraag"+std::to_string(i));
        int g = antw.empty()?-1:std::stoi(antw);
        bool ok = (g==q.vragen[i].antwoord); if(ok) goed++;
        ss << "<div style=\"background:rgba(" << (ok?"76,175,80":"255,82,82") << ",.15);border:1px solid " << (ok?"#69f0ae":"#ff5252") << ";border-radius:10px;padding:15px;margin-bottom:10px\">"
        "<p><strong>Vraag " << i+1 << ":</strong> " << q.vragen[i].tekst << "</p>"
        "<p>" << char('A'+g) << ". " << q.vragen[i].opties[g] << "</p>"
        << (!ok?std::string("<p style=\"color:#ff5252\">Fout. Het was: ")+char('A'+q.vragen[i].antwoord)+". "+q.vragen[i].opties[q.vragen[i].antwoord]+"</p>":std::string("<p style=\"color:#69f0ae\">Goed!</p>")) << "</div>";
    }
    int perc = tot>0 ? goed*100/tot : 0;
    ss << "<div class=\"stat-card\" style=\"max-width:400px;margin-bottom:30px\"><div class=\"getal\" style=\"color:" << (perc>=70?"#69f0ae":perc>=50?"#ffd740":"#ff8a80") << "\">" << goed << "/" << tot << "</div>"
    << "<div class=\"label\">" << perc << "% Goed</div></div>"
    "<a href=\"/leerling/quizzen\" class=\"btn btn-p\">Terug</a></div></body></html>";
}

// ================== LL DASHBOARD ==================
void maakLlDashboard(std::stringstream& ss, const std::string& naam, const std::string& klas) {
    ss << HDR1 << "<title>Dashboard</title></head><body>"; nav(ss,"leerling",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Welkom, <strong>" << naam << "</strong>! | " << klas << "</div>"
    "<div class=\"grid\"><div class=\"stat-card\"><div class=\"getal\">7.2</div><div class=\"label\">Gemiddeld</div></div>"
    "<div class=\"stat-card\"><div class=\"getal\">8</div><div class=\"label\">Cijfers</div></div>"
    "<div class=\"stat-card\"><div class=\"getal\">2</div><div class=\"label\">Openstaand</div></div></div>"
    "<div class=\"card\"><h2>Laatste Cijfers</h2><table><tr><th>Vak</th><th>Cijfer</th><th>Type</th></tr>"
    "<tr><td>Wiskunde</td><td style=\"color:#69f0ae\">8.5</td><td>Proefwerk</td></tr>"
    "<tr><td>Nederlands</td><td style=\"color:#69f0ae\">7.2</td><td>Huiswerk</td></tr></table></div></div></body></html>";
}

void maakSchoolgids(std::stringstream& ss, const std::string& naam) {
    ss << HDR1 << "<title>Schoolgids</title></head><body>"; nav(ss,"leerling",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Schoolgids voor <strong>" << naam << "</strong></div>"
    "<div class=\"grid\"><div class=\"card\"><h2>Schooluren</h2><table><tr><th>Les</th><th>Tijd</th></tr>"
    "<tr><td>1e</td><td>08:30-09:20</td></tr><tr><td>2e</td><td>09:25-10:15</td></tr><tr><td>3e</td><td>10:45-11:35</td></tr>"
    "<tr><td>4e</td><td>11:40-12:30</td></tr><tr><td>5e</td><td>13:15-14:05</td></tr><tr><td>6e</td><td>14:10-15:00</td></tr></table></div>"
    "<div class=\"card\"><h2>Contact</h2><p>Schoolstraat 1, Amsterdam</p><p>020-1234567</p></div></div></div></body></html>";
}

// ================== LIVE QUIZ PAGINA'S ==================
std::string maakQuizSpelPinPagina(const std::string& fout="") {
    std::stringstream ss;
    ss << HDR1 << "<title>Live Quiz</title></head><body><div style=\"display:flex;justify-content:center;align-items:center;min-height:100vh\"><div style=\"width:100%;max-width:450px;padding:20px\">"
    "<div style=\"text-align:center;margin-bottom:40px\"><h1 style=\"font-size:36px;color:#b388ff;margin-bottom:8px\">Live Quiz</h1><p style=\"color:#888\">Voer de spelcode in</p></div>";
    if (!fout.empty()) ss << "<div style=\"background:rgba(255,82,82,.2);border:1px solid #ff5252;border-radius:8px;padding:12px;margin-bottom:20px;color:#ff8a80;text-align:center\">" << fout << "</div>";
    ss << "<div class=\"card\"><form method=\"POST\" action=\"/leerling/quiz/spel\">"
    "<label class=\"f\">Spelcode<input type=\"text\" name=\"pin\" placeholder=\" Bijv. 1234\" pattern=\"[0-9]{4}\" required style=\"font-size:24px;text-align:center;letter-spacing:8px\"></label>"
    "<label class=\"f\">Jouw naam<input type=\"text\" name=\"speler\" placeholder=\"Jouw naam\" required></label>"
    "<button type=\"submit\" class=\"btn btn-p\" style=\"width:100%;padding:14px;font-size:16px\">Meedoen</button>"
    "</form></div></div></div></body></html>";
    return ss.str();
}

void maakDocentQuizBeheer(std::stringstream& ss, const std::string& naam) {
    ss << HDR1 << "<title>Live Quiz Beheer</title></head><body>"; nav(ss,"docent",naam);
    ss << "<div class=\"container\"><div class=\"welkom\"><strong>Live Quiz</strong> Beheer</div>";
    ss << "<div class=\"card\"><h2>Actieve Quizzen</h2><table><tr><th>PIN</th><th>Quiz</th><th>Vak</th><th>Klas</th><th>Spelers</th><th>Vraag</th><th>Acties</th></tr>";
    bool heeftActief = false;
    for (auto& aq : actieveQuizzen) {
        if (aq.quizIndex >= 0 && aq.quizIndex < (int)quizzen.size()) {
            heeftActief = true;
            auto& q = quizzen[aq.quizIndex];
            ss << "<tr><td style=\"font-size:24px;font-weight:bold;color:#b388ff\">" << aq.pin << "</td>"
            << "<td>" << q.titel << "</td><td>" << q.vak << "</td><td>" << q.klas << "</td>"
            << "<td>" << aq.spelers.size() << "</td><td>" << (aq.huidigeVraag+1) << "/" << q.vragen.size() << "</td>";
            if (aq.status == "wacht") {
                ss << "<td><form method=\"POST\" action=\"/docent/quiz/start\" style=\"display:inline\"><input type=\"hidden\" name=\"pin\" value=\"" << aq.pin << "\">"
                "<button type=\"submit\" class=\"btn btn-p\" style=\"padding:4px 12px\">Start</button></form>"
                "<form method=\"POST\" action=\"/docent/quiz/stop\" style=\"display:inline\"><input type=\"hidden\" name=\"pin\" value=\"" << aq.pin << "\">"
                "<button type=\"submit\" class=\"btn btn-d\" style=\"padding:4px 12px\">Stop</button></form></td></tr>";
            } else if (aq.status == "actief") {
                ss << "<td><form method=\"POST\" action=\"/docent/quiz/volgende\" style=\"display:inline\"><input type=\"hidden\" name=\"pin\" value=\"" << aq.pin << "\">"
                "<button type=\"submit\" class=\"btn btn-p\" style=\"padding:4px 12px\">Volgende</button></form>"
                "<form method=\"POST\" action=\"/docent/quiz/stop\" style=\"display:inline\"><input type=\"hidden\" name=\"pin\" value=\"" << aq.pin << "\">"
                "<button type=\"submit\" class=\"btn btn-d\" style=\"padding:4px 12px\">Stop</button></form></td></tr>";
            } else {
                ss << "<td><span class=\"badge badge-goed\">Klaar</span></td></tr>";
            }
        }
    }
    if (!heeftActief) ss << "<tr><td colspan=\"7\" style=\"text-align:center;color:#888\">Geen actieve quizzen</td></tr>";
    ss << "</table></div>";
    ss << "<div class=\"card\"><h2>Nieuwe Live Quiz</h2><form method=\"POST\" action=\"/docent/quiz/maak\">"
    "<label class=\"f\">Kies een Quiz<select name=\"quizIndex\">";
    for (int i=0; i<(int)quizzen.size(); i++) {
        ss << "<option value=\"" << i << "\">" << quizzen[i].titel << " (" << quizzen[i].vragen.size() << " vragen)</option>";
    }
    ss << "</select></label>"
    "<button type=\"submit\" class=\"btn btn-p\">Maak Live Quiz</button></form></div>";
    ss << "</div></body></html>";
}

void maakLeerlingQuizWacht(std::stringstream& ss, const std::string& naam, const std::string& pin) {
    ActieveQuiz* aq = vindActieveQuiz(pin);
    if (!aq || aq->quizIndex < 0 || aq->quizIndex >= (int)quizzen.size()) return;
    auto& q = quizzen[aq->quizIndex];
    ss << HDR1 << "<title>Wachten...</title></head><body>"; nav(ss,"leerling",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Quiz: <strong>" << q.titel << "</strong></div>"
    "<div class=\"card\" style=\"text-align:center;padding:50px\">"
    "<h2>Wacht op de docent</h2>"
    "<p style=\"margin-top:10px;color:#888\">Je bent ingeschreven. De docent start de quiz zodra iedereen klaar is.</p>"
    "<p style=\"margin-top:20px;font-size:18px;color:#b388ff\">Deelnemers: <span id=\"aantal\">" << aq->spelers.size() << "</span></p>"
    "<div id=\"lijst\">";
    for (auto& p : aq->spelers) ss << "<p style=\"color:#ccc\">" << p.first << "</p>";
    ss << "</div>"
    "<script>"
    "setInterval(function(){"
    "  var x=new XMLHttpRequest();"
    "  x.open('POST','/leerling/quiz/spel/"+pin+"/poll',true);"
    "  x.setRequestHeader('Content-type','application/x-www-form-urlencoded');"
    "  x.onload=function(){"
    "    if(x.status==200){"
    "      var d=JSON.parse(x.responseText);"
    "      document.getElementById('aantal').innerText=d.aantal;"
    "      var l='';"
    "      for(var i=0;i<d.deelnemers.length;i++) l+='<p style=\"color:#ccc\">'+d.deelnemers[i]+'</p>';"
    "      document.getElementById('lijst').innerHTML=l;"
    "      if(d.status==='actief') location.href='/leerling/quiz/spel/"+pin+"?antwoord';"
    "    }"
    "  };"
    "  x.send('pin="<<pin<<"');"
    "},2000);"
    "</script>"
    "</div></body></html>";
}

void maakLeerlingQuizVraag(std::stringstream& ss, const std::string& naam, const std::string& pin) {
    ActieveQuiz* aq = vindActieveQuiz(pin);
    if (!aq || aq->status != "actief" || aq->huidigeVraag < 0 || aq->huidigeVraag >= (int)quizzen[aq->quizIndex].vragen.size()) return;
    auto& q = quizzen[aq->quizIndex];
    auto& v = q.vragen[aq->huidigeVraag];
    ss << HDR1 << "<title>Vraag " << (aq->huidigeVraag+1) << "</title></head><body>"; nav(ss,"leerling",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Vraag <strong>" << (aq->huidigeVraag+1) << "/" << q.vragen.size() << "</strong></div>"
    "<div class=\"card\" style=\"text-align:center\"><h2 style=\"font-size:22px\">" << v.tekst << "</h2></div>";
    for (int o=0; o<4; o++) {
        ss << "<div class=\"card\" style=\"padding:20px;cursor:pointer\" onclick=\"document.getElementById('antwoord').value='" << o << "';this.querySelector('form').submit()\">"
        "<form method=\"POST\" action=\"/leerling/quiz/spel/antwoord\" style=\"display:none\">"
        "<input type=\"hidden\" name=\"pin\" value=\"" << pin << "\">"
        "<input type=\"hidden\" id=\"antwoord\" name=\"antwoord\" value=\"" << o << "\">"
        "</form>"
        "<span style=\"font-size:20px;font-weight:bold;color:#b388ff\">" << char('A'+o) << "</span> " << v.opties[o] << "</div>";
    }
    ss << "<meta http-equiv=\"refresh\" content=\"5\">"
    "</div></body></html>";
}

void maakLeerlingQuizResultaat(std::stringstream& ss, const std::string& naam, const std::string& pin) {
    ActieveQuiz* aq = vindActieveQuiz(pin);
    if (!aq || aq->quizIndex < 0 || aq->quizIndex >= (int)quizzen.size()) return;
    auto& q = quizzen[aq->quizIndex];
    int vraagIdx = aq->huidigeVraag;
    ss << HDR1 << "<title>Resultaat vraag " << (vraagIdx+1) << "</title></head><body>"; nav(ss,"leerling",naam);
    ss << "<div class=\"container\"><div class=\"welkom\">Vraag <strong>" << (vraagIdx+1) << "</strong> resultaat</div>";
    if (vraagIdx < (int)q.vragen.size()) {
        auto& v = q.vragen[vraagIdx];
        ss << "<div class=\"card\"><h2>" << v.tekst << "</h2><p style=\"font-size:18px;color:#69f0ae\">Antwoord: " << v.opties[v.antwoord] << "</p></div>";
    }
    ss << "<div class=\"card\"><h2>Scorebord</h2><table><tr><th>Naam</th><th>Score</th></tr>";
    std::vector<std::pair<std::string, int>> gerangschikt;
    for (auto& p : aq->spelers) gerangschikt.push_back(p);
    std::sort(gerangschikt.begin(), gerangschikt.end(), [](auto& a, auto& b){ return a.second > b.second; });
    for (auto& p : gerangschikt) {
        ss << "<tr><td>" << p.first << "</td><td style=\"color:#b388ff;font-size:20px\">" << p.second << "</td></tr>";
    }
    ss << "</table></div>";
    if (vraagIdx+1 < (int)q.vragen.size()) {
        ss << "<p style=\"text-align:center;color:#888\">Volgende vraag binnenkort...</p>";
        ss << "<meta http-equiv=\"refresh\" content=\"5\">";
    } else {
        ss << "<div class=\"card\" style=\"text-align:center\"><h2>Quiz afgelopen!</h2><a href=\"/leerling/quizzen\" class=\"btn btn-p\">Terug</a></div>";
    }
    ss << "</div></body></html>";
}

// ================== HTTP ==================
void verstuur(SOCKET c, const std::string& st, const std::string& h, const std::string& b) {
    std::string a = "HTTP/1.1 "+st+"\r\nContent-Type: text/html; charset=UTF-8\r\n"+h+"Content-Length: "+std::to_string(b.length())+"\r\nConnection: close\r\n\r\n"+b;
    send(c, a.c_str(), (int)a.length(), 0);
}

// ================== MAIN ==================
int main() {
    WSADATA wd; WSAStartup(MAKEWORD(2,2), &wd);
    GebruikersDatabase db;
    SessieBeheerder sb;

    SOCKET srv = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    int opt=1; setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));
    sockaddr_in a; a.sin_family=AF_INET; a.sin_addr.s_addr=INADDR_ANY; a.sin_port=htons(8080);
    bind(srv, (sockaddr*)&a, sizeof(a));
    listen(srv, 20);

    std::cout << "SchoolPortaal snel klaar op http://localhost:8080\nCtrl+C om te stoppen.\n";
    std::cout.flush();

    char bigbuf[65536];

    while (true) {
        SOCKET cli = accept(srv, nullptr, nullptr);
        if (cli==INVALID_SOCKET) continue;

        int br = recv(cli, bigbuf, sizeof(bigbuf)-1, 0);
        if (br <= 0) { closesocket(cli); continue; }
        bigbuf[br] = 0;

        std::string req(bigbuf, br);
        size_t sp1 = req.find(" "), sp2 = req.find(" ", sp1+1);
        if (sp1==std::string::npos || sp2==std::string::npos) { closesocket(cli); continue; }
        std::string pad = req.substr(sp1+1, sp2-sp1-1);
        std::string methode = req.substr(0, sp1);
        std::string sid = haalCookie(req, "sessie_id");
        std::string pb = "";
        if (methode=="POST") { size_t bp=req.find("\r\n\r\n"); if(bp!=std::string::npos) pb=req.substr(bp+4); }

        std::stringstream ss;
        std::string eh = "";

        if (pad=="/") {
            Sessie* s = sb.haalOp(sid);
            if (!s) { ss << inlogPagina(); }
            else if (s->rol=="docent") maakDashboard(ss,s->naam,s->vak,"docent");
            else maakLlDashboard(ss,s->naam,s->klas);
        } else if (pad=="/inloggen" && methode=="POST") {
            std::string un=postWaarde(pb,"gebruikersnaam"), ww=postWaarde(pb,"wachtwoord"), rl=postWaarde(pb,"rol");
            Gebruiker* g = db.vind(un, ww);
            if (g && g->rol==rl) { eh="Set-Cookie: sessie_id="+sb.maakSessie(*g)+"; Path=/; HttpOnly\r\nLocation: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
            else ss << inlogPagina("Ongeldig.");
        } else if (pad=="/uitloggen") {
            if (!sid.empty()) sb.verwijder(sid);
            eh="Set-Cookie: sessie_id=; Path=/; Max-Age=0\r\nLocation: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;
        } else if (pad=="/docent" || pad=="/docent/") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="docent") maakDashboard(ss,s->naam,s->vak,"docent"); else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad=="/docent/cijfers") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="docent") maakCijfers(ss,s->naam,s->vak); else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad=="/docent/klassen") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="docent") maakKlassen(ss,s->naam); else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad=="/docent/toetsen" && methode=="GET") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="docent") maakToetsen(ss,s->naam,s->vak); else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad=="/docent/toetsen" && methode=="POST") {
            Sessie* s = sb.haalOp(sid);
            if(s&&s->rol=="docent"){Toets t;t.titel=postWaarde(pb,"titel");t.vak=postWaarde(pb,"vak");t.klas=postWaarde(pb,"klas");t.datum=postWaarde(pb,"datum");t.tijd=postWaarde(pb,"tijd");t.beschrijving=postWaarde(pb,"beschrijving");t.duur=postWaarde(pb,"duur").empty()?60:std::stoi(postWaarde(pb,"duur"));t.aangemaakt_door=s->naam;toetsen.push_back(t);}
            eh="Location: /docent/toetsen\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;
        } else if (pad=="/docent/toetsen/verwijder" && methode=="POST") {
            Sessie* s = sb.haalOp(sid);
            if(s&&s->rol=="docent"){std::string idx=postWaarde(pb,"index");if(!idx.empty()){int i=std::stoi(idx);if(i>=0&&i<(int)toetsen.size())toetsen.erase(toetsen.begin()+i);}}
            eh="Location: /docent/toetsen\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;
        } else if (pad=="/docent/leerlingen") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="docent") maakLeerlingen(ss,s->naam); else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad=="/docent/quizzen" && methode=="GET") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="docent") maakQuizOverzicht(ss,s->naam,s->vak); else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad=="/docent/quizzen" && methode=="POST") {
            Sessie* s = sb.haalOp(sid);
            if(s&&s->rol=="docent"){Quiz q;q.titel=postWaarde(pb,"titel");q.vak=postWaarde(pb,"vak");q.klas=postWaarde(pb,"klas");q.beschrijving=postWaarde(pb,"beschrijving");q.aangemaakt_door=s->naam;quizzen.push_back(q);}
            eh="Location: /docent/quizzen\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;
        } else if (pad=="/docent/quizzen/verwijder" && methode=="POST") {
            Sessie* s = sb.haalOp(sid);
            if(s&&s->rol=="docent"){std::string idx=postWaarde(pb,"index");if(!idx.empty()){int i=std::stoi(idx);if(i>=0&&i<(int)quizzen.size())quizzen.erase(quizzen.begin()+i);}}
            eh="Location: /docent/quizzen\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;
        } else if (pad.find("/docent/quiz/")==0 && pad.find("/vraag")==std::string::npos && methode=="GET") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="docent") maakQuizDetail(ss,s->naam,std::stoi(pad.substr(13)));
            else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad.find("/docent/quiz/")==0 && pad.find("/vraag")!=std::string::npos && methode=="POST") {
            Sessie* s = sb.haalOp(sid);
            if(s&&s->rol=="docent"){int idx=std::stoi(pad.substr(13,pad.find("/",13)-13));Vraag v;v.tekst=postWaarde(pb,"vraag");v.opties[0]=postWaarde(pb,"opt0");v.opties[1]=postWaarde(pb,"opt1");v.opties[2]=postWaarde(pb,"opt2");v.opties[3]=postWaarde(pb,"opt3");v.antwoord=std::stoi(postWaarde(pb,"antwoord"));quizzen[idx].vragen.push_back(v);
            eh="Location: /docent/quiz/"+std::to_string(idx)+"\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;}
        } else if (pad=="/leerling" || pad=="/leerling/") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="leerling") maakLlDashboard(ss,s->naam,s->klas); else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad=="/leerling/cijfers") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="leerling") maakLkCijfers(ss,s->naam,s->klas); else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad=="/leerling/quizzen") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="leerling") maakLkQuizzen(ss,s->naam); else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad.find("/leerling/quiz/")==0 && methode=="GET" && pad.find("/antwoord")==std::string::npos) {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="leerling") maakLkQuizMaken(ss,s->naam,std::stoi(pad.substr(15)));
            else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad.find("/leerling/quiz/")==0 && methode=="POST") {
            Sessie* s = sb.haalOp(sid);
            if(s&&s->rol=="leerling") { int idx=std::stoi(pad.substr(15,pad.find("/",15)-15)); maakLkQuizResultaat(ss,s->naam,idx,pb); }
            else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad=="/leerling/schoolgids") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="leerling") maakSchoolgids(ss,s->naam); else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad=="/leerling/quiz/spel" && methode=="GET") {
            ss << maakQuizSpelPinPagina();
        } else if (pad=="/leerling/quiz/spel" && methode=="POST") {
            std::string pin = postWaarde(pb,"pin");
            std::string speler = postWaarde(pb,"speler");
            ActieveQuiz* aq = vindActieveQuiz(pin);
            if (aq && aq->status=="wacht") {
                aq->spelers[speler] = 0;
                eh="Location: /leerling/quiz/spel/"+pin+"\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;
            } else {
                ss << maakQuizSpelPinPagina("Ongeldige code of quiz niet beschikbaar.");
            }
        } else if (pad.find("/leerling/quiz/spel/")==0 && methode=="GET" && pad.find("/antwoord")==std::string::npos) {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="leerling") {
                std::string pin = pad.substr(20);
                ActieveQuiz* aq = vindActieveQuiz(pin);
                if (aq && aq->status=="actief") maakLeerlingQuizVraag(ss,s->naam,pin);
                else if (aq) maakLeerlingQuizWacht(ss,s->naam,pin);
                else ss << "<html><body><p>Ongeldige PIN. <a href=\"/leerling/quiz/spel\">Opnieuw</a></p></body></html>";
            } else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad.find("/leerling/quiz/spel/")==0 && methode=="POST" && pad.find("/poll")!=std::string::npos) {
            std::string pin = postWaarde(pb,"pin");
            ActieveQuiz* aq = vindActieveQuiz(pin);
            if (aq) {
                std::stringstream json;
                json << "{\"status\":\"" << aq->status << "\",\"aantal\":" << aq->spelers.size() << ",\"deelnemers\":[";
                bool eerste = true;
                for (auto& p : aq->spelers) {
                    if (!eerste) json << ",";
                    json << "\"" << p.first << "\"";
                    eerste = false;
                }
                json << "]}";
                std::string j = json.str();
                verstuur(cli, "200 OK", "Content-Type: application/json\r\n", j);
                closesocket(cli); continue;
            }
        } else if (pad.find("/leerling/quiz/spel/")==0 && methode=="POST" && pad.find("/antwoord")!=std::string::npos) {
            std::string pin = postWaarde(pb,"pin");
            int antwoord = std::stoi(postWaarde(pb,"antwoord"));
            ActieveQuiz* aq = vindActieveQuiz(pin);
            if (aq && aq->status=="actief") {
                aq->antwoorden[sb.haalOp(sid)->naam] = antwoord;
                if (antwoord == quizzen[aq->quizIndex].vragen[aq->huidigeVraag].antwoord) {
                    aq->spelers[sb.haalOp(sid)->naam] += 10;
                }
                eh="Location: /leerling/quiz/spel/"+pin+"\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;
            }
        } else if (pad=="/docent/quiz/beheer" && methode=="GET") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="docent") maakDocentQuizBeheer(ss,s->naam); else { eh="Location: /\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue; }
        } else if (pad=="/docent/quiz/maak" && methode=="POST") {
            Sessie* s = sb.haalOp(sid); if(s&&s->rol=="docent") {
                int idx = std::stoi(postWaarde(pb,"quizIndex"));
                if (idx>=0 && idx<(int)quizzen.size()) {
                    ActieveQuiz aq;
                    aq.pin = genereerPin();
                    aq.quizIndex = idx;
                    aq.status = "wacht";
                    aq.huidigeVraag = 0;
                    aq.startTijd = time(nullptr);
                    actieveQuizzen.push_back(aq);
                }
            }
            eh="Location: /docent/quiz/beheer\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;
        } else if (pad=="/docent/quiz/start" && methode=="POST") {
            ActieveQuiz* aq = vindActieveQuiz(postWaarde(pb,"pin"));
            if (aq) aq->status = "actief";
            eh="Location: /docent/quiz/beheer\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;
        } else if (pad=="/docent/quiz/volgende" && methode=="POST") {
            ActieveQuiz* aq = vindActieveQuiz(postWaarde(pb,"pin"));
            if (aq && aq->quizIndex<(int)quizzen.size()) {
                aq->huidigeVraag++;
                aq->antwoorden.clear();
                if (aq->huidigeVraag >= (int)quizzen[aq->quizIndex].vragen.size()) {
                    aq->status = "klaar";
                }
            }
            eh="Location: /docent/quiz/beheer\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;
        } else if (pad=="/docent/quiz/stop" && methode=="POST") {
            std::string stopPin = postWaarde(pb,"pin");
            for (auto it = actieveQuizzen.begin(); it != actieveQuizzen.end(); ++it) {
                if (it->pin == stopPin) { actieveQuizzen.erase(it); break; }
            }
            eh="Location: /docent/quiz/beheer\r\n"; verstuur(cli,"302 Found",eh,""); closesocket(cli); continue;
        } else {
            ss << "<html><body style=\"font-family:sans-serif;text-align:center;padding:50px\"><h1>404</h1><p><a href=\"/\">Terug</a></p></body></html>";
        }

        std::string body = ss.str();
        verstuur(cli, "200 OK", eh, body);
        closesocket(cli);
    }
    closesocket(srv); WSACleanup();
    return 0;
}