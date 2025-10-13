package main

// go run line_counter.go

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const (
	Reset  = "\033[0m"
	Red    = "\033[31m"
	Green  = "\033[32m"
	Yellow = "\033[33m"
	Blue   = "\033[34m"
	Cyan   = "\033[36m"
	White  = "\033[37m"
	Bold   = "\033[1m"
)

// countLines counts the number of lines in a given file.
func countLines(filePath string) (int, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return 0, err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	lines := 0
	for scanner.Scan() {
		lines++
	}

	if err := scanner.Err(); err != nil {
		return 0, err
	}
	return lines, nil
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println(Cyan + "----------------------------------------------------" + Reset)
		fmt.Println(Bold + Green + "  Dosya Satır Sayacı - Kullanım Talimatları" + Reset)
		fmt.Println(Cyan + "----------------------------------------------------" + Reset)
		fmt.Println(Yellow + "Kullanım:" + Reset + " go run line_counter.go <dizin_yolu>")
		fmt.Println(Yellow + "Örnek:" + Reset + " go run line_counter.go . ")
		fmt.Println(White + "       (Mevcut dizindeki dosyaları tarar ve uzantıyı sorar)" + Reset)
		fmt.Println(Yellow + "Örnek:" + Reset + " go run line_counter.go /home/user/projeler ")
		fmt.Println(White + "       ('/home/user/projeler' dizinindeki dosyaları tarar ve uzantıyı sorar)" + Reset)
		fmt.Println(Cyan + "----------------------------------------------------" + Reset)
		return
	}

	rootDir := os.Args[1]

	fmt.Printf(Yellow + "\nHangi dosya uzantısını taramak istersiniz (örn: txt, go, md)? " + Reset)
	reader := bufio.NewReader(os.Stdin)
	inputExtension, _ := reader.ReadString('\n')
	fileExtension := "." + strings.TrimSpace(strings.TrimPrefix(inputExtension, ".")) // Ensure extension starts with a dot and trim whitespace

	fmt.Printf(Cyan + "\n----------------------------------------------------\n" + Reset)
	fmt.Printf(Bold+Blue+"  '%s' dizininde '%s' uzantılı dosyalar taranıyor...\n"+Reset, rootDir, fileExtension)
	fmt.Printf(Cyan + "----------------------------------------------------\n" + Reset)

	var totalLines int
	var filesProcessed int
	var errorsEncountered int

	err := filepath.Walk(rootDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			fmt.Printf(Red+"HATA: '%s' dizinine erişilemiyor veya taranamıyor: %v\n"+Reset, path, err)
			errorsEncountered++
			return nil // Hata olsa bile diğer dosyalara devam et
		}
		if !info.IsDir() && strings.HasSuffix(info.Name(), fileExtension) {
			lines, err := countLines(path)
			if err != nil {
				fmt.Printf(Red+"HATA: '%s' dosyası okunurken sorun oluştu: %v\n"+Reset, path, err)
				errorsEncountered++
				return nil // Hata olsa bile diğer dosyalara devam et
			}
			totalLines += lines
			filesProcessed++
		}
		return nil
	})

	fmt.Printf(Cyan + "\n----------------------------------------------------\n" + Reset)
	fmt.Println(Bold + Green + "  Tarama Tamamlandı!" + Reset)
	fmt.Printf(Cyan + "----------------------------------------------------\n" + Reset)

	if err != nil {
		fmt.Printf(Red+"GENEL HATA: Dizin gezme işlemi tamamlanamadı: %v\n"+Reset, err)
	}

	fmt.Printf(White+"Taranan Dizin: %s\n"+Reset, rootDir)
	fmt.Printf(White+"Aranan Uzantı: %s\n"+Reset, fileExtension)
	fmt.Printf(White+"İşlenen Dosya Sayısı: %d\n"+Reset, filesProcessed)
	fmt.Printf(White+"Toplam Satır Sayısı: %d\n"+Reset, totalLines)
	if errorsEncountered > 0 {
		fmt.Printf(Yellow+"Karşılaşılan Hata Sayısı: %d (Yukarıdaki detaylara bakın)\n"+Reset, errorsEncountered)
	}
	fmt.Printf(Cyan + "----------------------------------------------------\n" + Reset)
}
