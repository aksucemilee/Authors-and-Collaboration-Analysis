import pandas as pd
from pyvis.network import Network
import html
from flask import Flask, render_template_string, jsonify, request
from collections import deque
import ast
import os
import time
from threading import Thread

app = Flask(__name__)


class Graf:
    def __init__(self):
        self.nodes = {}
        self.edges = {}

    def add_node(self, node_id, label=None, size=10, color="blue", info="", paper_title1=None):

        if node_id not in self.nodes:
            if paper_title1 is None:
                paper_title1 = set()
            self.nodes[node_id] = {"label": label or node_id, "size": size, "color": color, "info": info,
                                   "paper_title1": paper_title1}

    def add_edge(self, baslangic_dugum, hedef_dugum, paper_title):

        key = tuple(sorted([baslangic_dugum, hedef_dugum]))
        if key not in self.edges:
            self.edges[key] = {"makaleler": [], "weight": 0}
        if paper_title not in self.edges[key]["makaleler"]:
            self.edges[key]["makaleler"].append(paper_title)
            self.edges[key]["weight"] += 1


class Binary_Node:
    def __init__(self, key):
        self.sol = None
        self.sag = None
        self.key = key


class Binary_Tree:
    def __init__(self):
        self.root = None

    def insert(self, key):
        if not self.root:
            self.root = Binary_Node(key)
        else:
            self.recursive_insert(self.root, key)

    def recursive_insert(self, dugum, key):
        if key > dugum.key:
            if dugum.sag:
                self.recursive_insert(dugum.sag, key)
            else:
                dugum.sag = Binary_Node(key)
        elif key < dugum.key:
            if dugum.sol:
                self.recursive_insert(dugum.sol, key)
            else:
                dugum.sol = Binary_Node(key)

    def sil(self, key):
        self.root = self.recursive_sil(self.root, key)

    def recursive_sil(self, dugum, key):
        if not dugum:
            return dugum
        if key > dugum.key:
            dugum.sag = self.recursive_sil(dugum.sag, key)
        elif key < dugum.key:
            dugum.sol = self.recursive_sil(dugum.sol, key)
        else:
            if not dugum.sag:
                return dugum.sol
            elif not dugum.sol:
                return dugum.sag

            temp = self.min_deger(dugum.sag)
            dugum.key = temp.key
            dugum.sag = self.recursive_sil(dugum.sag, temp.key)
        return dugum

    def min_deger(self, dugum):
        deger = dugum
        while deger.sol:
            deger = deger.sol
        return deger

    def sirala(self):
        sonuc = []
        self.listele(self.root, sonuc)
        return sonuc

    def listele(self, dugum,
                sonuc):
        if dugum:
            self.listele(dugum.sol, sonuc)
            sonuc.append(dugum.key)
            self.listele(dugum.sag, sonuc)

def transfer_to_pyvis_bst(Binary_Tree, id_kaldir):
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    net.toggle_physics(False)
    #net.barnes_hut()

    root_key = Binary_Tree.root.key if Binary_Tree.root else None

    def dugum_kenar_ekle(dugum):
        if dugum:
            if dugum.key == root_key:
                color = "purple"
            elif dugum.key == id_kaldir:
                color = "red"
            else:
                color = "white"
            net.add_node(
                dugum.key,
                label=dugum.key,
                color=color,
                title=f"Yazar ID: {dugum.key}"
            )
            if dugum.sol:
                dugum_kenar_ekle(dugum.sol)
                net.add_edge(dugum.key, dugum.sol.key)
            if dugum.sag:
                dugum_kenar_ekle(dugum.sag)
                net.add_edge(dugum.key, dugum.sag.key)


    dugum_kenar_ekle(Binary_Tree.root)

    return net

def read_excel(excel_dosya_yolu):
    return pd.read_excel(excel_dosya_yolu)

def graf_olustur(okunanveri, limit=1000):
    graf = Graf()
    islenen_veri = okunanveri.iloc[:limit]
    eklenen_dugum = set()
    mevcut_kenar = set()
    orcid_set = set()

    toplam_makale = okunanveri.groupby('orcid')['paper_title'].nunique()
    ortalama_makale = toplam_makale.mean()

    def yazar_dugum_ekle(orcid, author_name, yazar_makale):
        """Merkez yazarı düğüm olarak ekler."""
        if orcid not in eklenen_dugum:
            size, color = dugum_boyut_ve_renk(yazar_makale, ortalama_makale)
            author_papers = okunanveri[okunanveri['orcid'] == orcid]['paper_title'].unique()
            info = f"Yazar: {author_name}\nORCID: {orcid}\nToplam Makale Sayısı: {yazar_makale}\nMakaleler:\n" + "\n".join(
                author_papers)  # join kullanmamın sebebi \n kullanııp alt alta yazması icin
            graf.add_node(node_id=orcid, label=author_name, size=size, color=color, info=info,
                          paper_title1=set(author_papers))
            eklenen_dugum.add(orcid)
            orcid_set.add(orcid)

    def ortak_yazar_dugum_ve_kenar_ekle(orcid, author_name, coauthors, paper_title, author_position):
        """Ortak yazarlar için düğüm ve kenar ekler."""
        if isinstance(coauthors, str):
            coauthors = ast.literal_eval(coauthors)

        coauthors = [coauthor.strip() for coauthor in coauthors if
                     coauthor.strip().lower() != author_name.strip().lower()]

        for coauthor in coauthors:

            if coauthor not in eklenen_dugum:
                paper_set = {paper_title}
                size, color = dugum_boyut_ve_renk(len(paper_set), ortalama_makale)
                info = f"Ortak Yazar: {coauthor}\nToplam Makale Sayısı:{len(paper_set)}\nMakaleler:\n" + "\n".join(
                    paper_set)
                graf.add_node(node_id=coauthor, label=coauthor, size=size, color=color, info=info,
                              paper_title1=paper_set)
                eklenen_dugum.add(coauthor)
            else:
                paper_set = graf.nodes[coauthor]["paper_title1"]
                paper_set.add(paper_title)
                yeni_sayac = len(paper_set)
                yeni_info = (f"Ortak Yazar: {coauthor}\nToplam Makale Sayısı: {yeni_sayac}\nMakaleler:\n" + "\n".join(
                    paper_set))
                graf.nodes[coauthor]["info"] = yeni_info

            graf.add_edge(orcid, coauthor, paper_title)

    def dugum_boyut_ve_renk(yazar_makale, ortalama_makale):
        """Düğüm boyutu ve rengini belirler."""
        if yazar_makale > ortalama_makale * 1.2:
            return 40, "red"  # %20 üzerinde
        elif yazar_makale < ortalama_makale * 0.8:
            return 20, "lightblue"  # %20 altında
        else:
            return 30, "orange"  # Ortalama civarı


    for index, satir in islenen_veri.iterrows():
        orcid = satir['orcid']
        author_name = satir['author_name']
        paper_title = satir['paper_title']
        coauthors = satir['coauthors']
        author_position = satir['author_position']

        # Merkez yazar düğümü ekle
        yazar_makale = toplam_makale.get(orcid, 0)
        yazar_dugum_ekle(orcid, author_name, yazar_makale)

        ortak_yazar_dugum_ve_kenar_ekle(orcid, author_name, coauthors, paper_title, author_position)
    print(f"orcid düğüm sayısı: {len(orcid_set)}")
    return graf

def transfer_to_pyvis(olusan_graf, vurgulanan_dugum=[], vurgulanan_kenar=[]):
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    net.toggle_physics(True)
    # net.barnes_hut()

    # Düğümleri ekle
    for node_id, data in olusan_graf.nodes.items():
        color = "yellow" if node_id in vurgulanan_dugum else data["color"]
        net.add_node(
            node_id,
            label=data["label"],
            size=data["size"],
            color=color,
            title=data["info"],
        )

    for (baslangic_dugum, hedef_dugum), edge_data in olusan_graf.edges.items():
        paper_titles = edge_data["makaleler"]
        weight = edge_data["weight"]

        escaped_titles = [html.escape(str(title)) for title in paper_titles]  # BU SATIRI EKLEYİN
        title = f"Ortak Makale:{weight}\n" + " \n".join(escaped_titles)

        if (baslangic_dugum, hedef_dugum) in vurgulanan_kenar or (hedef_dugum, baslangic_dugum) in vurgulanan_kenar:
            color = "red"
            width = 5
        else:
            color = "grey"
            width = weight

        net.add_edge(baslangic_dugum, hedef_dugum, title=title, value=weight, width=width, color=color)

    return net


def EnKisaYol_Hesapla(graf, baslangic_dugumu):
    mesafe = {}
    for dugum in graf.nodes:
        if dugum == baslangic_dugumu:
            mesafe[dugum] = 0
        else:
            mesafe[dugum] = float('inf')

    print("Başlangıçta mesafeler:", mesafe)

    ziyaretedilen_dugumler = set()
    komsu_dugumler = [(baslangic_dugumu, 0)]

    while komsu_dugumler:
        print("komsu_dugumler:", komsu_dugumler)
        anlik_dugum, anlik_mesafe = komsu_dugumler.pop(0)
        print(f"Anlik dugum: {anlik_dugum}, Mesafe: {anlik_mesafe}")
        ziyaretedilen_dugumler.add(anlik_dugum)

        for (source, target), komsu_mesafe in graf.edges.items():
            if anlik_dugum == source:
                diger_dugum = target
            elif anlik_dugum == target:
                diger_dugum = source
            else:
                continue

            if diger_dugum not in ziyaretedilen_dugumler:
                yeni_mesafe = anlik_mesafe + komsu_mesafe['weight']
                print(f"Kontrol edilen kenar: ({source}, {target}), Kenar agirligi: {komsu_mesafe['weight']}")
                print(f"Yeni mesafe: {yeni_mesafe} (eğer {diger_dugum}) için)")
                if yeni_mesafe < mesafe[diger_dugum]:
                    mesafe[diger_dugum] = yeni_mesafe
                    print(f"Güncel mesafe: {diger_dugum} -> {yeni_mesafe}")
                    komsu_dugumler.append((diger_dugum, yeni_mesafe))
                    print("Ziyaret edilen düğümler:", ziyaretedilen_dugumler)

    print("Son mesafe:", mesafe)
    return mesafe


def EnUzunYol_Hesapla(graf, baslangic_dugumu):
    ziyaretedilen_dugumler = set()
    dugum_stack = [(baslangic_dugumu, 1, [baslangic_dugumu])]
    max_yol = 0
    maxyol_dugum = []

    while dugum_stack:
        anlik_dugum, yol_uzunlugu, dugum = dugum_stack.pop()

        if anlik_dugum in ziyaretedilen_dugumler:
            continue

        ziyaretedilen_dugumler.add(anlik_dugum)

        if yol_uzunlugu > max_yol:
            max_yol = yol_uzunlugu
            maxyol_dugum = dugum

        for (source, target), _ in graf.edges.items():
            if source == anlik_dugum and target not in ziyaretedilen_dugumler:
                dugum_stack.append((target, yol_uzunlugu + 1, dugum + [target]))
            elif target == anlik_dugum and source not in ziyaretedilen_dugumler:
                dugum_stack.append((source, yol_uzunlugu + 1, dugum + [source]))

    return maxyol_dugum, max_yol

@app.route("/")
def gorsel():
    global olusan_graf
    excel_dosya_yolu = r"C:\Users\Lenovo\Downloads\PROLAB 3 - GÜNCEL DATASET.xlsx"  # excel

    okunanveri = read_excel(excel_dosya_yolu)
    olusan_graf = graf_olustur(okunanveri)

    net = transfer_to_pyvis(olusan_graf)

    toplam_node = len(olusan_graf.nodes)
    toplam_edge = len(olusan_graf.edges)

    print(f"toplam node {toplam_node}")
    print(f"toplam edge {toplam_edge}")
    html_output = net.generate_html()
    custom_html = """
        <div style="position:fixed; left:10px; top:50px; width:300px; height:600px;border-radius:10px; background:rgba(249, 249, 249, 0.5); padding:15px;overflow-y:scroll;">
            <h3 style="text-align:center;">ÇIKTI EKRANI</h3>
             <div id="output-content" style="font-size:14px; white-space:pre-wrap; background-color:#f9f9f9; padding:10px; border:1px solid #ccc;"></div>
        </div>
        <div style="position:fixed; right:10px; top:50px; width:150px;height:600px;border-radius:10px; background:rgba(249, 249, 249, 0.5); padding-top:35px;overflow-y:scroll;display: flex; flex-direction: column; align-items: center; justify-content: space-between;">
            <!-- <h4 style="text-align:center;">İSTERLER</h4>  -->

           <div id="id-input-container" style="display:none; margin-bottom:20px; width:100%">
               <input id="author-id" type="text" placeholder="ID Girin" style="width:90%; margin-bottom: 0 auto 10px; display:block;">
               <input id="author-id-2" type="text" placeholder="ID Girin" style="width:90%; margin-bottom: 0 auto 10px; display:none;">
               <button id="submit-id" style="width:90%; height:40px; border-radius:10px; background-color:#007BFF; color:white; border:none; cursor:pointer; margin:10px auto; display:block;" onclick="submitID()">ID Gönder</button>
           </div>

            <button onclick="callAPI('/api/ister1', 1)" style="width:80%; height:40px; margin-bottom:10px; border-radius:10px; background:rgba(135, 206, 235, 0.5)">1. İSTER</button>
            <button onclick="callAPI('/api/ister2', 2)" style="width:80%; height:40px; margin-bottom:10px; border-radius:10px; background:rgba(135, 206, 235, 0.5)">2. İSTER</button>
            <button onclick="callAPI('/api/ister3', 3)" style="width:80%; height:40px; margin-bottom:10px; border-radius:10px; background:rgba(135, 206, 235, 0.5)">3. İSTER</button>
            <button onclick="callAPI('/api/ister4', 4)" style="width:80%; height:40px; margin-bottom:10px; border-radius:10px; background:rgba(135, 206, 235, 0.5)">4. İSTER</button>
            <button onclick="callAPI('/api/ister5', 5)" style="width:80%; height:40px; margin-bottom:10px; border-radius:10px; background:rgba(135, 206, 235, 0.5)">5. İSTER</button>
            <button onclick="callAPI('/api/ister6', 6)" style="width:80%; height:40px; margin-bottom:10px; border-radius:10px; background:rgba(135, 206, 235, 0.5)">6. İSTER</button>
            <button onclick="callAPI('/api/ister7', 7)" style="width:80%; height:40px; margin-bottom:10px; border-radius:10px; background:rgba(135, 206, 235, 0.5)">7. İSTER</button> 
        </div>
        <script>

            const requiresIDList = [1, 2, 3, 4, 5, 7];
            let calisanIster = null;
            let highlightedNode = null;
            let pollingInterval = null;

            function callAPI(url,isterSayi) { 
                calisanIster = isterSayi;

                if (requiresIDList.includes(isterSayi)) {
                   document.getElementById('id-input-container').style.display = 'block';
                   if (isterSayi === 1) {
                       document.getElementById('author-id-2').style.display = 'block';
                   } else {
                        document.getElementById('author-id-2').style.display = 'none'; 
                   }
                } else {
                    document.getElementById('id-input-container').style.display = 'none';
                    fetchData(url);
                }
            }

             function submitID() {
                const id1 = document.getElementById('author-id').value;
                const id2 = document.getElementById('author-id-2').value;

                if(!calisanIster){
                   alert("Lütfen bir ister seçiniz.");
                   return;
                }
                console.log("Gönderilen ID1:", id1, "Gönderilen ID2:", id2);
                if (calisanIster === 1) {
                    if (!id1 || !id2) {
                        console.error("1. İster için iki ID'nin doldurulması gerekiyor.");
                        alert("Lütfen iki ID'yi de doldurun!");
                        return;
                    }
                      ister1_basla(id1,id2);
                }
                if (calisanIster === 2) {
                    if (!id1) { 
                       console.error("ID girilmesi gerekiyor.");
                       alert("Lütfen bir ID girin!");
                       return; 
                    }
                    ister2_basla(id1); 
                }
                if (calisanIster === 3) {
                    if (!id1) { 
                       console.error("ID girilmesi gerekiyor.");
                       alert("Lütfen bir ID girin!");
                       return; 
                    }
                    ister3_basla(id1); // Özel fonksiyonu çağır
                }
                else {
                    const url = `/api/ister${calisanIster}`;
                    if (!id1) {
                        console.error("ID girilmesi gerekiyor.");
                        alert("Lütfen bir ID girin!");
                        return;
                    }
                    const body = { id1 };
                    fetchData(url, body);
                }
             }

             function fetchData(url, body = null) {
                 if (!url) {
                    console.error("URL tanımlı değil!");
                    return;
                 }

                 const options = body
                    ? {
                       method: 'POST',
                       headers: { 'Content-Type': 'application/json' },
                       body: JSON.stringify(body),
                    }
                 : {};

                 fetch(url, options)
                    .then(response => {
                       if (!response.ok) {
                          return response.json().then(data => {
                          document.getElementById('output-content').innerHTML = data.result;
                          throw new Error(data.result); 
                       });
                    }
                    return response.json();
                 })
                .then(data => {
                   console.log("Sunucudan Gelen Yanıt:", data);
                   document.getElementById('output-content').innerHTML = data.result;
                })
                .catch(error => {
                   console.error('Error:', error);
                   document.getElementById('output-content').innerText = "Bir hata oluştu.";
                });
             }

            function ister1_basla(id1, id2){
                fetch(`/api/ister1`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({id1, id2})
                })
                .then(resp => {
                    if(!resp.ok) throw new Error("Sunucu hatası");
                    return resp.json();
                })
                .then(data => {
                    document.getElementById('output-content').innerText = data.result;
                    pollingInterval = setInterval(() => {
                        fetchIster1Status(id1, id2);
                    }, 1000); //saniyede bir
                })
                .catch(err => {
                    console.error("Fetch Error:", err);
                    document.getElementById('output-content').innerText = "Bir hata oluştu.";
                });
            }

            function fetchIster1Status(id1, id2){
                fetch(`/api/ister1/status?id1=${encodeURIComponent(id1)}&id2=${encodeURIComponent(id2)}`)
                    .then(resp => {
                        if(!resp.ok) throw new Error("Sunucu hatası");
                        return resp.json();
                    })
                    .then(data => {
                        document.getElementById('output-content').innerText = data.steps.join("\\n");

                        if(data.path){
                            highlightPath(data.path);
                        }

                        if(data.completed){
                            clearInterval(pollingInterval);
                        }
                    })
                    .catch(err => {
                        console.error("Fetch Error:", err);
                        document.getElementById('output-content').innerText = "Bir hata oluştu.";
                        clearInterval(pollingInterval);
                });
            }

            function ister2_basla(id1){ 
                fetch(`/api/ister2`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({id1})
                })
                .then(resp => {
                    if(!resp.ok) throw new Error("Sunucu hatası");
                    return resp.json();
                })
                .then(data => {
                    document.getElementById('output-content').innerText = data.result;
                    pollingInterval = setInterval(() => {
                        fetchIster2Status(id1);
                    }, 1000); //saniyede bir
                })
                .catch(err => {
                    console.error("Fetch Error:", err);
                    document.getElementById('output-content').innerText = "Bir hata oluştu.";
                });
            }

            function fetchIster2Status(id1){
                fetch(`/api/ister2/status?id1=${encodeURIComponent(id1)}`)
                    .then(resp => {
                        if(!resp.ok) throw new Error("Sunucu hatası");
                        return resp.json();
                    })
                    .then(data => {
                        const output = data.steps.join("\\n");
                        document.getElementById('output-content').innerText = output;

                        if(data.current_node){
                            nodeBelirt(data.current_node);
                            document.getElementById('output-content').innerText += "\\n[Şu an işlenen düğüm]: " + data.current_node;
                        }

                        if(data.completed){
                            clearInterval(pollingInterval);
                            if(highlightedNode){
                                network.body.data.nodes.update([{ id: highlightedNode, color: 'blue' }]);
                                highlightedNode = null;
                            }
                        }
                    })
                    .catch(err => {
                        console.error("Fetch Error:", err);
                        document.getElementById('output-content').innerText = "Bir hata oluştu.";
                        clearInterval(pollingInterval);
                    });
            }

            function ister3_basla(id1){
                fetch(`/api/ister3`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({id1})
                })
                .then(resp => {
                    if(!resp.ok) throw new Error("Sunucu hatası");
                    return resp.json();
                })
                .then(data => {
                    document.getElementById('output-content').innerText = data.result;
                    pollingInterval = setInterval(() => {
                        ister3Status();
                    }, 1000); // 1 saniyede bir
                })
                .catch(err => {
                    console.error("Fetch Error:", err);
                    document.getElementById('output-content').innerText = "Bir hata oluştu.";
                });
            }
            function ister3Status(){
                fetch(`/api/ister3/status`)
                    .then(resp => {
                        if(!resp.ok) throw new Error("Sunucu hatası");
                        return resp.json();
                    })
                    .then(data => {
                        let output = data.steps.join("\\n");
                        if(data.completed){
                            fetch(`/api/ister3/bst`)
                                .then(resp => resp.json())
                                .then(bstData => {
                                    const iframe = document.createElement('iframe');
                                    iframe.style.width = "100%";
                                    iframe.style.height = "750px";
                                    iframe.srcdoc = bstData.result;
                                    const outputContainer = document.getElementById('output-content');
                                    outputContainer.innerHTML = ""; 
                                    outputContainer.appendChild(iframe);
                                    clearInterval(pollingInterval);
                                })
                                .catch(err => {
                                    console.error("Fetch Error:", err);
                                    document.getElementById('output-content').innerText = "Bir hata oluştu.";
                                    clearInterval(pollingInterval);
                                });
                        } else {
                            document.getElementById('output-content').innerText = output;
                        }
                    })
                    .catch(err => {
                        console.error("Fetch Error:", err);
                        document.getElementById('output-content').innerText = "Bir hata oluştu.";
                        clearInterval(pollingInterval);
                    });
            }

            function highlightPath(path){
                if(highlightedNode){
                    network.body.data.nodes.update([{ id: highlightedNode, color: network.body.data.nodes.get(highlightedNode).color }]);
                    highlightedNode = null;
                }

                for(let i=0; i<path.length; i++){
                    const nodeId = path[i];
                    network.body.data.nodes.update([{ id: nodeId, color: 'green' }]);
                    if(i < path.length -1){
                        const edge = network.getEdge(path[i], path[i+1]);
                        if(edge){
                            network.body.data.edges.update([{ id: edge.id, color: 'green' }]);
                        }
                    }
                }
            }

            function nodeBelirt(nodeId){
               if (!network.body.data.nodes.get(nodeId)) {
                  console.error(`Düğüm bulunamadı: ${nodeId}`);
                  return;
               }
               if (highlightedNode && highlightedNode !== nodeId){
                   network.body.data.nodes.update([{ id: highlightedNode, color: network.body.data.nodes.get(highlightedNode).color }]);
               }
               network.body.data.nodes.update([{ id: nodeId, color: 'pink' }]);
               network.focus(nodeId, {
                 scale: 1.5,
                 animation: { duration: 1000 }
               });
               highlightedNode = nodeId;
            }

        </script>
    """

    favicon_html = """
            <link rel="icon" href="data:,">
        """

    return render_template_string(html_output + custom_html + favicon_html)


@app.route("/popup_graph/<filename>")
def popup_graph(filename):
    file_path = f"./static/{filename}"
    try:
        with open(file_path, "r") as file:
            return file.read()
    except FileNotFoundError:
        return "<h1>Grafik bulunamadı!</h1>"


ister1_sirala = {}
ister1_sonuc = {}


@app.route("/api/ister1", methods=['POST'])
def ister1_basla():
    global olusan_graf, ister1_sirala, ister1_sonuc
    veri = request.get_json()
    id1 = veri.get('id1')
    id2 = veri.get('id2')

    if not olusan_graf:
        return jsonify({"result": "Graf bulunamadı!"}), 400

    if not id1 or not id2:
        return jsonify({"result": "İki yazar ID'si gereklidir!!"}), 400

    if id1 not in olusan_graf.nodes or id2 not in olusan_graf.nodes:
        return jsonify({"result": "Geçersiz Yazar ID'si girildi!!"}), 400

    key = (id1, id2)
    if key in ister1_sirala and not ister1_sirala[key]["completed"]:
        return jsonify({"result": "1.İster: Bu ID çifti için işlem zaten devam ediyor."}), 400

    ister1_sirala[key] = {
        "steps": [],
        "completed": False,
        "result": "",
        "path": []
    }

    thread = Thread(target=IkıDugum_MesafeHesapla, args=(id1, id2))
    thread.start()

    return jsonify({"result": f"1.İster için ID'ler alındı: 1. ID {id1}, 2. ID {id2}."})


def IkıDugum_MesafeHesapla(id1, id2):
    global olusan_graf, ister1_sirala, ister1_sonuc
    key = (id1, id2)
    try:

        kuyruk = deque()
        kuyruk.append([id1])
        tamamlanan = set()
        tamamlanan.add(id1)
        ister1_sirala[key]["steps"].append(f"Başlanan düğüm: {id1}")
        print(f"Başlanan düğüm: {id1}")

        while kuyruk:
            path = kuyruk.popleft()
            dugum = path[-1]

            ister1_sirala[key]["steps"].append(f"İşlenen düğüm: {dugum}")
            print(f"İşlenen düğüm: {dugum}")

            komsu_bul = []
            for (baslangic_dugum, hedef_dugum) in olusan_graf.edges:
                if baslangic_dugum == dugum:
                    komsu_bul.append(hedef_dugum)
                elif hedef_dugum == dugum:
                    komsu_bul.append(baslangic_dugum)

            print(f"Bulunan komşular: {komsu_bul}")
            ister1_sirala[key]["steps"].append(f"Oluşan kuyruk: {list(kuyruk)}")

            if dugum == id2:
                ister1_sirala[key]["steps"].append(f"[BİTTİ] Yol bulundu: {' -> '.join(path)}")
                ister1_sirala[key]["path"] = path
                ister1_sirala[key]["completed"] = True
                ister1_sirala[key]["result"] = f"1.İster tamamlandı.\nOluşan Yol: {' -> '.join(path)}"
                print(f"[BİTTİ] Yol bulundu: {' -> '.join(path)}")
                return

            for komsu in komsu_bul:
                if komsu not in tamamlanan:
                    yeni_path = list(path)
                    yeni_path.append(komsu)
                    kuyruk.append(yeni_path)
                    tamamlanan.add(komsu)
                    ister1_sirala[key]["steps"].append(f"Yeni yol eklendi: {' -> '.join(yeni_path)}")
                    print(f"Yeni yol eklendi: {' -> '.join(yeni_path)}")
                    time.sleep(0.5)

        ister1_sirala[key]["steps"].append(f"[BİTTİ] {id1} ile {id2} arasında yol mevcut değil.")
        ister1_sirala[key]["completed"] = True
        ister1_sirala[key]["result"] = f"1.İster tamamlandı.\n{id1} ile {id2} arasında yol mevcut değil!!"
        print(f"[BİTTİ] {id1} ile {id2} arasında yol mevcut değil.")
    except Exception as e:
        ister1_sirala[key]["steps"].append(f"[HATA] {str(e)}")
        ister1_sirala[key]["completed"] = True
        ister1_sirala[key]["result"] = f"1.İster Hatalı! {str(e)}"
        print(f"[HATA] {str(e)}")

@app.route("/api/ister1/status", methods=['GET'])
def ister1_status():
    id1 = request.args.get('id1', '').strip()
    id2 = request.args.get('id2', '').strip()
    key = (id1, id2)
    if not id1 or not id2:
        return jsonify({"result": "Eksik ID girildi."}), 400
    if key not in ister1_sirala:
        return jsonify({"result": "ID çifti mevcut değil."}), 400
    veri = {
        "steps": ister1_sirala[key]["steps"],
        "completed": ister1_sirala[key]["completed"],
        "result": ister1_sirala[key]["path"]
    }
    return jsonify(veri)


ister2_sirala = {}
ister2_sonuc = {}

@app.route("/api/ister2", methods=['POST'])
def ister2_basla():
    global ister2_sirala, ister2_sonuc
    veri = request.get_json()
    id1 = veri.get('id1')

    if not olusan_graf:
        return jsonify({"result": "Graf bulunamadı!"}), 400

    if not id1 or id1 not in olusan_graf.nodes:
        return jsonify({"result": "2.İster: Hatalı veya eksik ID!"}), 400

    if id1 in ister2_sirala:
        return jsonify({"result": "2.İster: Bu ID için işlem zaten devam ediyor."}), 400

    ister2_sirala[id1] = {
        "steps": [],
        "completed": False,
        "result": "",
        "current_node": None
    }

    thread = Thread(target=Dugum_Sirala, args=(id1,))
    thread.start()

    return jsonify({"result": f"2.İster için ID alındı: {id1}."})


def Dugum_Sirala(id1):
    global olusan_graf, ister2_sirala, ister2_sonuc
    try:
        isbirligi = set()
        for (baslangic, hedef) in olusan_graf.edges:
            if baslangic == id1 or hedef == id1:
                diger = baslangic if hedef == id1 else hedef
                isbirligi.add(diger)

        kuyruk_olustur = []
        adim_sayac = 1
        for yardimci_yazar in isbirligi:
            edge_key = tuple(sorted([id1, yardimci_yazar]))
            if edge_key in olusan_graf.edges:
                ortak_makale = olusan_graf.edges[edge_key]["makaleler"]
                makale_sayisi = len(ortak_makale)
                kuyruk_olustur.append((makale_sayisi, yardimci_yazar))
                kuyruk_olustur.sort(key=lambda x: x[0])

                ister2_sirala[id1]["current_node"] = yardimci_yazar

                ister2_sirala[id1]["steps"].append(
                    f"[ADIM-{adim_sayac}] {yardimci_yazar} eklendi, Makale: {makale_sayisi}")
                ister2_sirala[id1]["steps"].append(f"Sıralama sonrası kuyruk: {kuyruk_olustur}")
                adim_sayac += 1
                time.sleep(0.5)

        ister2_sirala[id1]["steps"].append(f"[BİTTİ] Toplam {len(kuyruk_olustur)} coauthor.")
        time.sleep(0.5)
        kuyruk_olustur.sort(key=lambda x: x[0])
        ister2_sirala[id1]["steps"].append(f"2.İster tamamlandı:\n{kuyruk_olustur}")
        ister2_sirala[id1]["completed"] = True
        ister2_sirala[id1]["result"] = f"2.İster tamamlandı:\n{kuyruk_olustur}"
        ister2_sirala[id1]["current_node"] = None
    except Exception as e:
        ister2_sirala[id1]["steps"].append(f"[HATA] {str(e)}")
        ister2_sirala[id1]["completed"] = True
        ister2_sirala[id1]["result"] = f"2.İster Hata: {str(e)}"
        ister2_sirala[id1]["current_node"] = None


@app.route("/api/ister2/status", methods=['GET'])
def ister2_status():
    id1 = request.args.get('id1', '').strip()
    if not id1:
        return jsonify({"result": "ID bulunamadı."}), 400
    if id1 not in ister2_sirala:
        return jsonify({"result": "ID için işlem bulunamadı."}), 400

    data = {
        "steps": ister2_sirala[id1]["steps"],
        "completed": ister2_sirala[id1]["completed"],
        "result": ister2_sirala[id1]["result"],
        "current_node": ister2_sirala[id1]["current_node"]
    }
    return jsonify(data)


ister3_sirala = {}
ister3_sonuc = {}


@app.route("/api/ister3", methods=['POST'])
def ister3_basla():
    global olusan_graf, ister3_sirala, ister3_sonuc
    veri = request.get_json()
    id_kaldir = veri.get('id1')


    if not olusan_graf:
        return jsonify({"result": "Graf bulunamadı!!"}), 400

    if not id_kaldir:
        return jsonify({"result": "Yazar ID'si gerekli!!"}), 400
    if id_kaldir not in olusan_graf.nodes:
        return jsonify({"result": "Geçersiz Yazar ID'si girildi!!"}), 400

    tamamlanan_key = [anahtar for anahtar, deger in ister1_sirala.items() if deger["completed"]]
    if not tamamlanan_key:
        return jsonify({
            "result": """
                <div style="color:red; font-size:16px;">
                    Hata: Lütfen önce 1. İster'i çalıştırın ve tamamlayın!
                </div>
            """
        }), 400

    son_key = tamamlanan_key[-1]
    path = ister1_sirala[son_key]["path"]
    if not path:
        return jsonify({
            "result": """
                <div style="color:red; font-size:16px;">
                    Hata: 1. İster'den alınan yol boş. Lütfen verilerinizi kontrol edin.
                </div>
            """
        }), 400

    key = "ister3_default"
    if key in ister3_sirala and not ister3_sirala[key]["completed"]:
        return jsonify({"result": "3. İster işlemi zaten devam ediyor!"}), 400

    ister3_sirala[key] = {"steps": [], "completed": False, "result": "", "bst": None}
    thread = Thread(target=BinaryTree_Olustur, args=(key, id_kaldir))
    thread.start()

    return jsonify({"result": "3. İster başlatıldı."})


@app.route("/api/ister3/status", methods=['GET'])
def ister3_status():
    key = "ister3_default"
    if key not in ister3_sirala:
        return jsonify({"result": "İşlem bulunamadı."}), 400
    veri = {
        "steps": ister3_sirala[key]["steps"],
        "completed": ister3_sirala[key]["completed"],
        "result": ister3_sirala[key]["result"]
    }
    return jsonify(veri)


def BinaryTree_Olustur(key, id_kaldir):

    global olusan_graf, ister3_sirala, ister3_sonuc, ister1_sirala
    try:
        tamamlanan_key = [anahtar for anahtar, deger in ister1_sirala.items() if deger["completed"]]
        if not tamamlanan_key:
            raise ValueError("`ister1` henüz tamamlanmadı.")

        son_key = tamamlanan_key[-1]
        path = ister1_sirala[son_key]["path"]
        if not path:
            raise ValueError("`ister1`'den yol alınamadı.")

        binary_tree = Binary_Tree()
        for author in path:
            binary_tree.insert(author)
            ister3_sirala[key]["steps"].append(f"{author} Binary Search Tree'ye eklendi.")

        binary_tree.sil(id_kaldir)
        ister3_sirala[key]["steps"].append(f"{id_kaldir} Binary Search Tree'den çıkarıldı.")

        son_bst = binary_tree.sirala()
        ister3_sirala[key]["steps"].append(f"BST'nin in-order traversali: {son_bst}")
        ister3_sirala[key]["completed"] = True
        ister3_sirala[key]["result"] = son_bst

        ister3_sirala[key]["bst"] = binary_tree

    except Exception as e:
        ister3_sirala[key]["steps"].append(f"[HATA] {str(e)}")
        ister3_sirala[key]["completed"] = True
        ister3_sirala[key]["result"] = f"3. İster Hatalı! {str(e)}"


@app.route("/api/ister3/bst", methods=['GET'])
def ister3_bst():
    key = "ister3_default"
    if key not in ister3_sirala or not ister3_sirala[key]["completed"]:
        return jsonify({"result": "BST henüz oluşturulmadı veya işlem devam ediyor."}), 400

    binary_tree = ister3_sirala[key].get("bst")
    if not binary_tree:
        return jsonify({"result": "BST bulunamadı."}), 400

    id_kaldir = None
    bst_graph = transfer_to_pyvis_bst(binary_tree, id_kaldir)
    file_name = "bst_graph.html"
    file_path = f"./static/{file_name}"
    bst_graph.save_graph(file_path)


    result_html = f"""
    <div>
        <p>3. İster tamamlandı: Binary Search Tree görselleştirildi.</p>
        <button onclick="window.open('/popup_graph/{file_name}', '_blank', 'width=800,height=600');">
            BST Grafiğini Göster
        </button>
    </div>
    """
    return jsonify({"result": result_html})


@app.route("/api/ister4", methods=['POST'])
def ister4():
    veri = request.get_json()
    if not veri or 'id1' not in veri:
        return jsonify({"result": "ID değeri eksik veya gönderilmemiş!"}), 400

    baslangic_dugumu = veri.get('id1')
    if baslangic_dugumu not in olusan_graf.nodes:
        return jsonify({"result": f"{baslangic_dugumu} ID'sine sahip yazar bulunamadı!"})

    baslangic_adi = olusan_graf.nodes[baslangic_dugumu]['label']

    enkisa_yol = EnKisaYol_Hesapla(olusan_graf, baslangic_dugumu)

    komsu_dugumler = [
        dugum for dugum, mesafe in enkisa_yol.items()
        if dugum != baslangic_dugumu and mesafe != float('inf')
    ]

    if not komsu_dugumler:
        result_html = f"""
        <div style="font-size:16px; font-weight:bold; margin-bottom:10px;">
            {baslangic_adi} ID'sine sahip yazarın hiçbir yardımcı yazarı bulunmamaktadır.
        </div>
        """
    else:
        html_table = """
        <table border="1" style="width:100%; border-collapse:collapse;">
            <thead>
                <tr>
                    <th>Düğüm</th>
                    <th>Mesafe</th>
                </tr>
            </thead>
            <tbody>
        """
        for dugum, mesafe in enkisa_yol.items():
            if dugum == baslangic_dugumu:
                continue
            if mesafe != float('inf'):
                dugum_adi = olusan_graf.nodes[dugum]['label']
                html_table += f"<tr><td>{dugum_adi}</td><td>{mesafe}</td></tr>"

        html_table += """
            </tbody>
        </table>
        """
        result_html = f"""
        <div style="font-size:16px; font-weight:bold; margin-bottom:10px;">
            <span style="color:#333;">En kısa yollar:</span> {baslangic_adi}
        </div>
        {html_table}
        """

    return jsonify({"result": result_html})


@app.route("/api/ister5", methods=['POST'])
def ister5():
    ortak_yazar = set()
    veri = request.get_json()
    id1 = veri.get('id1')

    print("Gelen İstek: /api/ister5")
    print(f"Gelen ID: {id1}")

    if not id1:
        return jsonify({"result": "ID mevcut değil."})

    for (baslangic_dugum, hedef_dugum), edge_data in olusan_graf.edges.items():
        if baslangic_dugum == id1 or hedef_dugum == id1:
            ortak_yazar.add(baslangic_dugum if baslangic_dugum != id1 else hedef_dugum)
    yazar_sayisi = len(ortak_yazar)
    sonuc = f"{id1} ID'ye sahip A yazarının işbirliği yaptığı yazar sayısı:{yazar_sayisi}"
    print(f"Sonuç: {sonuc}")  # Hesaplanan sonucu konsola yazdır
    return jsonify({"result": f"5.İster çalıştı:{sonuc}"})


@app.route("/api/ister6", methods=['GET'])
def ister6():
    global olusan_graf
    isbirligi = {}
    for (baslangic_dugum, hedef_dugum), edge_data in olusan_graf.edges.items():
        isbirligi[baslangic_dugum] = isbirligi.get(baslangic_dugum, 0) + 1
        isbirligi[hedef_dugum] = isbirligi.get(hedef_dugum, 0) + 1
    yazar = max(isbirligi, key=isbirligi.get)
    maksimum_isbirligi = isbirligi[yazar]

    sonuc = f"En çok işbirliği yapan yazar:{yazar}\nToplam işbirliği:{maksimum_isbirligi}"
    print(f"Sonuç:{sonuc}")
    return jsonify({"result": f"6.İster çalıştı:{sonuc}"})


@app.route("/api/ister7", methods=['POST'])
def ister7():
    veri = request.get_json()
    baslangic_dugumu = veri.get('id1')

    if baslangic_dugumu not in olusan_graf.nodes:
        return jsonify({"result": f"{baslangic_dugumu} ID'sine sahip yazar bulunamadı!"})

    maxyol_dugum, max_yol = EnUzunYol_Hesapla(olusan_graf, baslangic_dugumu)
    if not maxyol_dugum:
        return jsonify({"result": "En uzun yol bulunamadı!"})

    en_uzun_yol_kenarlari = [
        tuple(sorted((maxyol_dugum[i], maxyol_dugum[i + 1])))
        for i in range(len(maxyol_dugum) - 1)
    ]

    tam_net = transfer_to_pyvis(
        olusan_graf,
        vurgulanan_dugum=maxyol_dugum,
        vurgulanan_kenar=en_uzun_yol_kenarlari
    )

    uzun_yol_graf = Graf()
    for node_id in maxyol_dugum:
        uzun_yol_graf.add_node(
            node_id=node_id,
            **olusan_graf.nodes[node_id]
        )
    for (baslangic, hedef) in en_uzun_yol_kenarlari:
        uzun_yol_graf.add_edge(baslangic, hedef, olusan_graf.edges[(baslangic, hedef)]["makaleler"])

    uzun_yol_net = transfer_to_pyvis(uzun_yol_graf)

    static_folder = "./static"
    if not os.path.exists(static_folder):
        os.makedirs(static_folder)

    tam_file_name = f"graph_{baslangic_dugumu}_tam.html"
    tam_file_path = os.path.join(static_folder, tam_file_name)
    tam_net.save_graph(tam_file_path)

    yol_file_name = f"graph_{baslangic_dugumu}_yol.html"
    yol_file_path = os.path.join(static_folder, yol_file_name)
    uzun_yol_net.save_graph(yol_file_path)

    result_html = f"""
        <div style="font-size:16px; font-weight:bold; color:#333; margin-bottom:10px;">
            {baslangic_dugumu} ID'sinden başlayarak gidebileceğiniz en uzun yol {max_yol} düğüm uzunluğundadır.
        </div>
        <div style="font-size:14px; color:#555;">
            En uzun yol üzerindeki düğümler: {' → '.join(maxyol_dugum)}
        </div>
        <button onclick="window.open('/popup_graph/{tam_file_name}', '_blank', 'width=800,height=600');">Tam Grafiği Göster</button>
        <button onclick="window.open('/popup_graph/{yol_file_name}', '_blank', 'width=800,height=600');">En Uzun Yol Grafiğini Göster</button>
    """
    return jsonify({"result": result_html})


if __name__ == "__main__":
    app.run(debug=True)