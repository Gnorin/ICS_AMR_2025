ICS_AMR_2025

#相關設定
1.Python
-下載需要用到的套件(可參考我們的code)
-MQTT broker IP填入電腦本機IP(CMD指令: ipconfig 查詢IPv4)
-ESP32-CAM在Arduino燒錄好後，會得到一串網址，該網址就是ESP32-CAM的原始控制介面
-若要單獨取得ESP32-CAM的影像串流介面，需在該網址後加上":81/stream"

2.Arduino(ESP32/ESP32-CAM)
*開發環境*
-Tools->Board->Boards Manager->安裝"esp32"
-<WiFi.h>: Wi-Fi功能 ; <PubSubClient.h>: MQTT通訊協議

*Wi-Fi&MQTT*
-ESP32只能連2.4GHz的網路，請確認Wi-Fi是連到2.4G的那一個
-請確認Wi-Fi帳號和密碼輸入正確
-MQTT broker IP填入電腦本機IP(CMD指令: ipconfig 查詢IPv4)

*小車相關*
-車子的相關設定可以參考我們的code
-由於左右馬達安裝方向相反，我們的程式碼已針對此進行調整:左右輪的驅動邏輯（High/Low）在設定上是相反的
-若左右馬達轉向相反，請檢查程式碼定義或對調馬達接線
-在硬體的部分，ESP32和L298N記得要共地!!!

*ESP32-CAM燒錄*
-ESP32-CAM的燒錄程式檔可參考Arduino IDE原始提供的: File->Examples->ESP32-Camera->CameraWebServer
-我們提供的CameraWebServer只是根據自身需求，更改了預設的串流視窗大小
-ESP32-CAM燒錄時與TTL模組的接線: 5V->VCC; GND->GND; U0R->TXD; U0T->RXD; IO0<->GND(ESP32-CAM自身)
-ESP32-CAM燒錄完成後把IO0<->GND這條線拔除，並按下RST鍵，即可得到串流網址
-若上述方法沒得到網址，同樣先將IO0<->GND這條線拔除，再拔掉USB重新插入
-每次燒錄都要記得接上IO0<->GND!!!!!


3.Node-RED
-在我們的專題中，主要是使用Node-RED來設計監控中心
-若想使用Node-RED，可參考網路上的下載教學(很簡單)
-有了Node-RED後可以直接匯入我們的JSON檔
-開啟Node-RED的方法: 打開CMD，輸入NODE-RED即可(大小寫沒影響)
-在我們專題所使用的MQTT Broker即是Node-RED中的外掛節點，在此我們不須額外下載Mosquitto，Node-RED同時擔任了MQTT Broker的身分
-需額外下載的模組(位於節點管理):node-red-contrib-aedes(上述所提的MQTT Broker); node-red-dashboard(儀表板=監控中心介面)
-須前往儀表板，只需在原始網址(撰寫流程的網址)上加上"/ui"




