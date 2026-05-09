package main

// Este import en GO se encarga de traer las librerías necesarias para el funcionamiento del programa.
import (
	"encoding/json" // Esta librería se utiliza para codificar y decodificar datos en formato JSON.
	"fmt" // Esta librería se utiliza para formatear cadenas de texto y realizar operaciones de entrada/salida.
	"log" // Esta librería se utiliza para registrar mensajes de error y eventos importantes en el programa.
	"net/http" // Esta librería se utiliza para crear un servidor HTTP y manejar las solicitudes entrantes.

	"github.com/MarcoGonzalez0/mail-analyzer/scanner/internal/dns" 
	// Esta es una importación personalizada que trae el paquete "dns" desde el proyecto "mail-analyzer". Este paquete probablemente contiene funciones relacionadas con la resolución de DNS, como la función "Lookup" que se utiliza en el código para obtener información DNS de un dominio.
)

// Estructuras para definir formato de solicitud y respuesta JSON para la API de escaneo de dominios.
type ScanRequest struct { // Espero recibir
	Domain string `json:"domain"`
}

type ScanResponse struct { // Respondo con
	Domain  string     `json:"domain"` 
	DNS     dns.Result `json:"dns"`
}

func scanHandler(w http.ResponseWriter, r *http.Request) {

	// Verificar que el método HTTP sea POST, si no lo es, se devuelve un error de "método no permitido".
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Decodificar el cuerpo de la solicitud JSON en una estructura ScanRequest. Si hay un error durante la decodificación, se devuelve un error de "solicitud inválida".
	var req ScanRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid request", http.StatusBadRequest)
		return
	}

	// Realizar la consulta DNS utilizando la función "Lookup" del paquete "dns". El resultado se almacena en la variable "dnsResult".
	dnsResult := dns.Lookup(req.Domain)

	resp := ScanResponse{
		Domain: req.Domain,
		DNS:    dnsResult,
	}

	// Establecer el encabezado de la respuesta para indicar que el contenido es JSON y luego codificar la estructura ScanResponse en formato JSON y enviarla como respuesta al cliente.
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

// La función main es el punto de entrada del programa. Aquí se configura el servidor HTTP para escuchar en el puerto 8080 y manejar las solicitudes a la ruta "/scan" utilizando la función "scanHandler". Si el servidor encuentra un error al iniciar, se registra el error y se detiene la ejecución del programa.
func main() {
	http.HandleFunc("/scan", scanHandler)
	fmt.Println("Scanner listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}