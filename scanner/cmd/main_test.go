package main

// Los tests del handler usan net/http/httptest — librería estándar de Go.
// Permite simular requests HTTP sin levantar un servidor real:
//   httptest.NewRequest  → crea un request falso en memoria
//   httptest.NewRecorder → captura lo que el handler escribe como respuesta
// Con esto podemos llamar a scanHandler directamente, como una función normal.

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// ─── Tests unitarios del handler ─────────────────────────────────────────────
// No hacen DNS real. Testean la capa HTTP: validación de método y cuerpo.

func TestHandlerMétodoInválido(t *testing.T) {
	// El handler solo acepta POST. Un GET debe devolver 405.
	req := httptest.NewRequest(http.MethodGet, "/scan", nil)
	w := httptest.NewRecorder()

	scanHandler(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("esperaba 405 Method Not Allowed, obtuve %d", w.Code)
	}
}

func TestHandlerCuerpoInválido(t *testing.T) {
	// Si el body no es JSON válido, el decoder falla y debe devolver 400.
	body := bytes.NewBufferString("esto no es json {{{")
	req := httptest.NewRequest(http.MethodPost, "/scan", body)
	w := httptest.NewRecorder()

	scanHandler(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("esperaba 400 Bad Request, obtuve %d", w.Code)
	}
}

func TestHandlerCuerpoVacío(t *testing.T) {
	// Un body vacío también falla el decode → 400.
	req := httptest.NewRequest(http.MethodPost, "/scan", nil)
	w := httptest.NewRecorder()

	scanHandler(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("esperaba 400 Bad Request, obtuve %d", w.Code)
	}
}

func TestHandlerRespuestaEsJSON(t *testing.T) {
	// Con dominio vacío el handler llama a dns.Lookup("") que devuelve errores,
	// pero el handler igual responde 200 con un JSON válido.
	// Esto testea que: la serialización funciona aunque Lookup no encuentre nada.
	body, _ := json.Marshal(ScanRequest{Domain: ""})
	req := httptest.NewRequest(http.MethodPost, "/scan", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	scanHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("esperaba 200 OK, obtuve %d", w.Code)
	}

	// Verificar que la respuesta sea JSON parseable con la estructura esperada
	var resp ScanResponse
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("la respuesta no es JSON válido: %v\nbody: %s", err, w.Body.String())
	}
}

// ─── Tests de integración del handler ────────────────────────────────────────
// Hacen DNS real. Se saltan con -short para no depender de red en CI rápido.

func TestHandlerIntegracionConGoogleCom(t *testing.T) {
	if testing.Short() {
		t.Skip("saltando: requiere DNS real, usar sin -short para correr")
	}

	body, _ := json.Marshal(ScanRequest{Domain: "google.com"})
	req := httptest.NewRequest(http.MethodPost, "/scan", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	scanHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("esperaba 200 OK, obtuve %d\nbody: %s", w.Code, w.Body.String())
	}

	var resp ScanResponse
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("respuesta no parseable: %v", err)
	}

	// Verificamos los datos reales de google.com
	if resp.Domain != "google.com" {
		t.Errorf("esperaba domain='google.com', obtuve '%s'", resp.Domain)
	}
	if len(resp.DNS.ARecords) == 0 {
		t.Error("google.com debería tener A records")
	}
	if !resp.DNS.HasMX {
		t.Error("google.com debería tener MX records")
	}
	if !resp.DNS.HasSPF {
		t.Error("google.com debería tener SPF")
	}
	if !resp.DNS.HasDMARC {
		t.Error("google.com debería tener DMARC")
	}
}
