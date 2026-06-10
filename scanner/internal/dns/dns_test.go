package dns

import (
	"net"
	"testing"
)

// ─── Tests unitarios ─────────────────────────────────────────────────────────
// Testean la lógica del struct Result y funciones auxiliares
// sin hacer llamadas de red reales.

func TestResultInicial(t *testing.T) {
	// Un Result recién creado debe tener todos los campos en sus zero values
	result := Result{}

	if result.HasMX {
		t.Error("HasMX debería ser false en un Result vacío")
	}
	if result.HasSPF {
		t.Error("HasSPF debería ser false en un Result vacío")
	}
	if result.HasDMARC {
		t.Error("HasDMARC debería ser false en un Result vacío")
	}
	if len(result.Errors) != 0 {
		t.Error("Errors debería estar vacío en un Result vacío")
	}
}

func TestDeteccionSPF(t *testing.T) {
	// Simulo lo que haría Lookup cuando encuentra TXT records:
	// recorro los registros y marco HasSPF si encuentro "v=spf1"
	// Esto testea la lógica de detección sin hacer DNS real.

	tests := []struct {
		nombre   string
		records  []string
		esperado bool
	}{
		{
			nombre:   "sin registros TXT",
			records:  nil,
			esperado: false,
		},
		{
			nombre:   "con SPF válido",
			records:  []string{"v=spf1 include:_spf.google.com -all"},
			esperado: true,
		},
		{
			nombre:   "TXT sin SPF",
			records:  []string{"google-site-verification=abc123"},
			esperado: false,
		},
		{
			nombre:   "SPF entre otros registros",
			records:  []string{"google-site-verification=abc", "v=spf1 -all", "otro=valor"},
			esperado: true,
		},
		{
			nombre:   "string corto que empieza con v=spf",
			records:  []string{"v=spf"},
			esperado: false, // "v=spf" tiene 5 chars, la condición pide > 6
		},
	}

	for _, tc := range tests {
		t.Run(tc.nombre, func(t *testing.T) {
			// Reproduzco la misma lógica que Lookup usa para detectar SPF
			hasSPF := false
			for _, txt := range tc.records {
				if len(txt) > 6 && txt[:6] == "v=spf1" {
					hasSPF = true
				}
			}
			if hasSPF != tc.esperado {
				t.Errorf("esperaba HasSPF=%v para records %v, obtuve %v",
					tc.esperado, tc.records, hasSPF)
			}
		})
	}
}

func TestDeteccionDMARC(t *testing.T) {
	tests := []struct {
		nombre   string
		records  []string
		esperado bool
		cantidad int // cuántos registros DMARC válidos se esperan
	}{
		{
			nombre:   "sin registros",
			records:  nil,
			esperado: false,
			cantidad: 0,
		},
		{
			nombre:   "con DMARC válido",
			records:  []string{"v=DMARC1; p=reject; pct=100"},
			esperado: true,
			cantidad: 1,
		},
		{
			nombre:   "registro que no es DMARC",
			records:  []string{"v=spf1 -all"},
			esperado: false,
			cantidad: 0,
		},
		{
			nombre:   "string corto que empieza con v=DMARC",
			records:  []string{"v=DMARC"},
			esperado: false, // "v=DMARC" tiene 7 chars, la condición pide > 8
		},
	}

	for _, tc := range tests {
		t.Run(tc.nombre, func(t *testing.T) {
			// Reproduzco la lógica de Lookup para detectar DMARC
			hasDMARC := false
			var dmarcRecords []string
			for _, txt := range tc.records {
				if len(txt) > 8 && txt[:8] == "v=DMARC1" {
					hasDMARC = true
					dmarcRecords = append(dmarcRecords, txt)
				}
			}
			if hasDMARC != tc.esperado {
				t.Errorf("esperaba HasDMARC=%v, obtuve %v", tc.esperado, hasDMARC)
			}
			if len(dmarcRecords) != tc.cantidad {
				t.Errorf("esperaba %d registros DMARC, obtuve %d", tc.cantidad, len(dmarcRecords))
			}
		})
	}
}

func TestFiltradoMX(t *testing.T) {
	// MX con host "." significa "este dominio no acepta correo" (null MX, RFC 7505)
	// Lookup debe filtrarlo y no contarlo como un MX válido

	tests := []struct {
		nombre       string
		mxRecords    []*net.MX
		esperadoHasMX bool
		esperadoCount int
	}{
		{
			nombre:        "MX válidos",
			mxRecords:     []*net.MX{{Host: "mail.google.com.", Pref: 10}},
			esperadoHasMX: true,
			esperadoCount: 1,
		},
		{
			nombre:        "null MX (solo punto)",
			mxRecords:     []*net.MX{{Host: ".", Pref: 0}},
			esperadoHasMX: false,
			esperadoCount: 0,
		},
		{
			nombre:        "mezcla de válidos y null MX",
			mxRecords:     []*net.MX{{Host: ".", Pref: 0}, {Host: "mx1.example.com.", Pref: 10}},
			esperadoHasMX: true,
			esperadoCount: 1,
		},
		{
			nombre:        "sin registros MX",
			mxRecords:     nil,
			esperadoHasMX: false,
			esperadoCount: 0,
		},
	}

	for _, tc := range tests {
		t.Run(tc.nombre, func(t *testing.T) {
			// Reproduzco la lógica de filtrado de Lookup
			var mxList []string
			for _, mx := range tc.mxRecords {
				if mx.Host != "." {
					mxList = append(mxList, mx.Host)
				}
			}
			hasMX := len(mxList) > 0
			if hasMX != tc.esperadoHasMX {
				t.Errorf("esperaba HasMX=%v, obtuve %v", tc.esperadoHasMX, hasMX)
			}
			if len(mxList) != tc.esperadoCount {
				t.Errorf("esperaba %d MX records, obtuve %d", tc.esperadoCount, len(mxList))
			}
		})
	}
}

// ─── Tests de integración ────────────────────────────────────────────────────
// Estos SÍ hacen llamadas DNS reales. Dependen de internet y de que los
// registros DNS de google.com no cambien. Son frágiles pero valiosos como
// smoke test para verificar que la función Lookup funciona end-to-end.
//
// Para correr solo estos: go test -run TestIntegracion -v
// Para excluirlos:        go test -run "^Test[^I]" -v

func TestIntegracionLookupGoogle(t *testing.T) {
	if testing.Short() {
		t.Skip("saltando test de integración en modo -short")
	}

	result := Lookup("google.com")

	// google.com siempre tiene A records
	if len(result.ARecords) == 0 {
		t.Error("google.com debería tener A records")
	}

	// google.com siempre tiene MX records
	if !result.HasMX {
		t.Error("google.com debería tener MX records")
	}

	// google.com siempre tiene SPF
	if !result.HasSPF {
		t.Error("google.com debería tener SPF")
	}

	// google.com tiene DMARC
	if !result.HasDMARC {
		t.Error("google.com debería tener DMARC")
	}

	// No debería tener errores
	if len(result.Errors) > 0 {
		t.Errorf("no se esperaban errores, obtuve: %v", result.Errors)
	}
}

func TestIntegracionLookupDominioInexistente(t *testing.T) {
	if testing.Short() {
		t.Skip("saltando test de integración en modo -short")
	}

	result := Lookup("este-dominio-no-existe-xyz-12345.com")

	// Un dominio inexistente no tiene nada
	if result.HasMX {
		t.Error("dominio inexistente no debería tener MX")
	}
	if result.HasSPF {
		t.Error("dominio inexistente no debería tener SPF")
	}
	if result.HasDMARC {
		t.Error("dominio inexistente no debería tener DMARC")
	}
}
