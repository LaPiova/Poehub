# PoeHub Project Structure & Class Interactions

This document visualizes the high-level architecture of the PoeHub project, showing how the main Red-DiscordBot Cog (`PoeHub`) interacts with various services and the API client layer.

## Class Interaction Graph

```mermaid
classDiagram
    class PoeHub {
        +Config config
        +ChatService chat_service
        +BillingService billing
        +ContextService context_service
        +SummarizerService summarizer
        +ConversationStorageService conversation_manager
        +EncryptionHelper encryption
        +MusicService music_service
        -_auto_clear_loop()
        -_reminder_loop()
    }

    class MusicService {
        +search(keyword)
        +get_song_url(source, id)
        +add_to_queue(guild_id, song)
        +play_song(voice_client, song)
        +play_next(voice_client)
        +skip(voice_client)
        +get_volume(guild_id)
        +set_volume(guild_id, level)
    }

    class ChatService {
        +process_chat_request()
        +stream_response()
        +get_response()
        -BaseLLMClient client
        -RequestOptimizer optimizer
        -ThreadSafeMemory _memories
    }

    class BaseLLMClient {
        <<Abstract>>
        +stream_chat()
        +get_models()
        +format_image_message()
    }

    class OpenAIProvider {
        +stream_chat()
        +fetch_openrouter_pricing()
    }

    class AnthropicProvider {
        +stream_chat()
    }
    
    class GeminiProvider {
        +stream_chat()
    }
    
    class DummyProvider {
        +stream_chat()
    }

    class RequestOptimizer {
        +optimize_request()
        -analyzer_client
    }

    class SummarizerService {
        +summarize_messages()
        -_generate_summary()
    }

    class BillingService {
        +check_budget()
        +update_spend()
        -PricingOracle oracle
    }

    class ContextService {
        +get_user_language()
        +get_user_system_prompt()
    }

    class ConversationStorageService {
        +process_conversation_data()
        +prepare_for_storage()
        -EncryptionHelper encryption
    }

    class EncryptionHelper {
        +encrypt()
        +decrypt()
    }
    
    class PricingCrawler {
        +fetch_rates()
    }

    class PricingOracle {
        +calculate_cost()
        +load_dynamic_rates()
    }

    %% Main Cog Relationships
    PoeHub --> ChatService : initializes & uses
    PoeHub --> BillingService : initializes & uses
    PoeHub --> ContextService : initializes & uses
    PoeHub --> SummarizerService : initializes & uses
    PoeHub --> ConversationStorageService : initializes & uses
    PoeHub --> EncryptionHelper : initializes & uses
    PoeHub --> MusicService : initializes & uses

    %% Service Dependencies
    ChatService --> BaseLLMClient : uses for API
    ChatService --> RequestOptimizer : uses for query analysis
    ChatService --> BillingService : checks budget/updates spend
    ChatService --> ContextService : gets user settings
    ChatService --> ConversationStorageService : loads/saves history

    %% Inheritance / Implementation
    BaseLLMClient <|-- OpenAIProvider
    BaseLLMClient <|-- AnthropicProvider
    BaseLLMClient <|-- GeminiProvider
    BaseLLMClient <|-- DummyProvider

    %% Other Relationships
    SummarizerService --> ChatService : uses (as client)
    BillingService --> PricingOracle : uses for cost calcs
    BillingService ..> PricingCrawler : fetches data (optional)
    ConversationStorageService --> EncryptionHelper : uses
    RequestOptimizer ..> BaseLLMClient : gets client for analysis
```

## Component Overview

### Core
*   **PoeHub**: The central Cog that integrates with Red-DiscordBot. It handles commands (slash & text), events, and background loops (auto-clear, reminders). It initializes and coordinates all other services.

### Service Layer
*   **ChatService**: The heart of the bot. It orchestrates the flow from receiving a Discord message -> checking billing -> loading context -> optimizing request -> streaming from API -> updating Discord message.
*   **BillingService**: Manages quotas, budgets, and tracks spending per user/guild. It relies on `PricingOracle` for cost calculations.
*   **ContextService**: Abstraction for retrieving user and guild configuration (system prompts, languages, active conversation IDs).
*   **SummarizerService**: Provides map-reduce style summarization for long conversation histories, leveraging the `ChatService` to generate summaries.
*   **RequestOptimizer**: Analyzes user queries (using a lightweight model) to dynamically adjust parameters like `web_search`, `thinking_level`, etc.
*   **ConversationStorageService**: Handles the secure storage (encryption/decryption) of conversation history in the bot's config.
*   **MusicService**: Manages music search (via TuneFree API), audio playback, playlist queue, and volume control for voice channels.

### Infrastructure / API
*   **BaseLLMClient**: Abstract interface for different AI providers.
*   **OpenAIProvider**: Implementation for OpenAI-compatible APIs (including Poe, DeepSeek, OpenRouter).
*   **EncryptionHelper**: Handles Fernet encryption for data at rest.
