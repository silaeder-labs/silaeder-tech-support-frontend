package main

import (
	"log"
	"os"

	"tech-support-mixer/backend/internal/httpserver"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	server := httpserver.New("./public")
	if err := server.Start(":" + port); err != nil {
		log.Fatal(err)
	}
}
