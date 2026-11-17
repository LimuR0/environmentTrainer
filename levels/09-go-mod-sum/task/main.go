package main

import (
	"fmt"
	"os"

	"github.com/google/uuid"
)

func main() {
	id := uuid.NewString()
	if _, err := uuid.Parse(id); err != nil {
		fmt.Fprintln(os.Stderr, "生成的 UUID 不合法:", err)
		os.Exit(1)
	}
	fmt.Println("ID:", id)
}
