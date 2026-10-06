# Galaxy Checkout Fixer 🚀

Solução definitiva para o erro impeditivo de compras na Samsung Galaxy Store em jogos como **Genshin Impact**, **Roblox**, **Honkai: Star Rail** e outros aplicativos.

---

### Mensagens de Erro Conhecidas

#### Português
> **"Não é possível concluir a compra. Foi detectado um acesso não autorizado na sua conta. Este pagamento será interrompido para proteger suas informações."**

#### English
> **"Unable to complete purchase. Unauthorized access to your account has been detected. This payment will be stopped to protect your information."**

#### Español
> **"No se puede completar la compra. Se ha detectado un acceso no autorizado a su cuenta. Este pago se detendrá para proteger su información."**

---

## Causa Raiz Técnica

**Não há invasão, fraude ou restrição na sua conta Samsung.**

1. **O Gatilho:** No Brasil e em outros países da América Latina, o Samsung Checkout carrega em segundo plano um script antifraude do domínio `i.konduto.com`.
2. **A Quebra do Certificado SSL:** Em março de 2026, a Konduto renovou seu certificado SSL usando a autoridade raiz `Sectigo Public Server Authentication Root R46`.
3. **Incompatibilidade no Android 13 e anteriores:** Aparelhos como Galaxy S20 FE não possuem essa chave raiz no repositório do sistema, gerando o erro de validação:
   ```text
   cr_X509Util: Failed to validate the certificate chain: Trust anchor for certification path not found.
   chromium: handshake failed, net_error -202 (ERR_CERT_AUTHORITY_INVALID)
   UnifiedPayment: [PaymentGatewayResponse] onReceivedSslError: primary error: 3 (SSL_UNTRUSTED)
   ```
4. **O Bug da Samsung:** O aplicativo de pagamento interpreta qualquer falha de SSL como violação de segurança e bloqueia a tela com a mensagem de acesso não autorizado.
5. **Como funciona a correção:** O sistema da Samsung ignora falhas comuns de rede em scripts secundários. Ao bloquear o domínio `i.konduto.com` antes do certificado ser requisitado, o checkout abre normalmente e a compra é finalizada com cupons e descontos.

---

## Formas de Solucionar

Você pode escolher qualquer um dos métodos abaixo.

---

### Método 1: Direto no Celular (Sem Computador e Sem Instalar Nada)

Este é o método mais prático para quem não quer usar computador nem instalar aplicativos adicionais no celular.

1. Abra o navegador do celular e entre em **nextdns.io**.
2. Crie uma conta gratuita.
3. No painel de controle, vá na aba **Denylist** e adicione:
   ```text
   i.konduto.com
   ```
4. Na aba **Setup**, copie o endereço do seu DNS Privado, no formato:
   ```text
   xxxxxx.dns.nextdns.io
   ```
5. No seu celular Samsung, acesse:
   **Configurações > Conexões > Mais configurações de conexão > DNS Privado**.
6. Selecione a opção **Nome do host do provedor de DNS Privado**, cole o endereço copiado e toque em **Salvar**.
7. Abra o jogo e faça a compra. O bloqueio continuará ativo tanto no Wi-Fi quanto no 4G ou 5G.

---

### Método 2: Pelo Roteador Wi-Fi (Corrige Todos os Aparelhos da Casa)

Se você tem acesso às configurações do roteador da sua casa:

1. Acesse o painel de administração do roteador pelo navegador.
2. Procure pela opção de **Bloqueio de Domínio**, **DNS Filter** ou **Controle Parental**.
3. Adicione `i.konduto.com` na lista de bloqueios.
4. Salve as alterações. Qualquer aparelho conectado a esse Wi-Fi conseguirá finalizar compras na Galaxy Store sem precisar alterar nenhuma configuração individual.

---

### Método 3: Aplicativo Local no Celular (RethinkDNS ou AdGuard)

Se preferir usar um aplicativo de gerenciamento de rede no Android:

1. Baixe o **RethinkDNS** ou **AdGuard** pela Google Play Store.
2. Na área de regras de firewall ou bloqueio de domínio, adicione uma regra para bloquear:
   ```text
   i.konduto.com
   ```
3. Ative a proteção e realize sua compra na Galaxy Store.

---

### Método 4: Usando o Galaxy Checkout Fixer para Windows

Para quem prefere uma ferramenta pronta no computador com ativação em um clique via cabo USB:

Baixe o executável [`GalaxyCheckoutFix.exe`](./GalaxyCheckoutFix.exe). Ele já vem com Python e utilitários ADB embutidos, sem necessidade de instalar dependências.

#### Passo a passo via USB:
1. Conecte o aparelho Samsung ao computador pelo cabo USB com a Depuração USB ativada.
2. Abra o executável. O aplicativo reconhecerá o modelo do aparelho.
3. Clique em **ATIVAR CORREÇÃO NO CELULAR**.
4. Abra o jogo no celular e conclua sua compra normalmente.
5. Ao finalizar, clique em **DESATIVAR CORREÇÃO NO CELULAR** ou simplesmente feche a janela.

---

## Licença

Uso pessoal e comunitário gratuito sob **Licença Não Comercial**.

**É expressamente proibida a comercialização, venda ou cobrança por acesso a este software, código-fonte ou documentação associada.**
