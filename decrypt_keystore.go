package main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/sha512"
	"encoding/base64"
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"os"

	"golang.org/x/crypto/pbkdf2"
)

var filepath = flag.String("f", "", "path to keystore file")

const (
	filePermission = 0600
	// Encryption Related constants
	iVLength        = 12
	saltLength      = 64
	iterationsCount = 10000
	keyLength       = 32
)

var version = []byte("v1")

func hashPassword(password, salt []byte) []byte {
	return pbkdf2.Key(password, salt, iterationsCount, keyLength, sha512.New)
}

func decrypt(reader io.Reader) {
	data, _ := ioutil.ReadAll(reader)
	salt := data[0:saltLength]
	iv := data[saltLength : saltLength+iVLength]
	encodedBytes := data[saltLength+iVLength:]
	password := []byte("")
	passwordBytes := hashPassword(password, salt)

	block, _ := aes.NewCipher(passwordBytes)
	// if err != nil {
	// 	return nil, fmt.Errorf("could not create the keystore cipher to decrypt the data: %s", err)
	// }

	aesgcm, _ := cipher.NewGCM(block)
	// if err != nil {
	// 	return nil, fmt.Errorf("could not create the keystore cipher to decrypt the data: %s", err)
	// }

	decodedBytes, _ := aesgcm.Open(nil, iv, encodedBytes, nil)
	// if err != nil {
	// 	return nil, fmt.Errorf("could not decrypt keystore data: %s", err)
	// }

	// return bytes.NewReader(decodedBytes), nil
	fmt.Printf(string(decodedBytes))

	// return decodedBytes, nil
}

func load(Path string) {

	f, err := os.OpenFile(Path, os.O_RDONLY, filePermission)
	if err != nil {
		// if os.IsNotExist(err) {
		// 	return nil
		// }
		panic(fmt.Sprintf("%v", err))
		// return err
	}
	defer f.Close()

	// if common.IsStrictPerms() {
	// 	if err := k.checkPermissions(k.Path); err != nil {
	// 		return err
	// 	}
	// }

	raw, err := ioutil.ReadAll(f)
	if err != nil {
		panic(fmt.Sprintf("%v", err))
		// return err
	}

	v := raw[0:len(version)]
	if !bytes.Equal(v, version) {
		panic(fmt.Sprintf("keystore format doesn't match expected version: '%s' got '%s'", version, v))
		// return fmt.Errorf("keystore format doesn't match expected version: '%s' got '%s'", version, v)
	}

	base64Content := raw[len(version):]
	if len(base64Content) == 0 {
		// return fmt.Errorf("corrupt or empty keystore")
		panic(fmt.Sprintf("corrupt or empty keystore"))
	}

	base64Decoder := base64.NewDecoder(base64.StdEncoding, bytes.NewReader(base64Content))
	decrypt(base64Decoder)
}

func main() {
	flag.Parse()
	load(*filepath)
	// load("/Users/jared/builds/beats/filebeat/filebeat-6.5.4-darwin-x86_64/filebeat.keystore")
}
