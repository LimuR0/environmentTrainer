package com.example;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.text.WordUtils;

public final class App {

    private App() {
    }

    public static String shout(String raw) {
        String trimmed = StringUtils.trimToEmpty(raw);
        return WordUtils.capitalizeFully(trimmed) + "!";
    }

    public static void main(String[] args) {
        System.out.println("APP OK " + shout("  env demo  "));
    }
}
