package com.securityfabric.qualitylab;

import android.app.Activity;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {
    private EditText email;
    private EditText password;
    private TextView status;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(48, 80, 48, 48);

        TextView heading = new TextView(this);
        heading.setId(View.generateViewId());
        heading.setText("Security Fabric Login");
        heading.setTextSize(24);
        layout.addView(heading);

        email = new EditText(this);
        email.setId(R.id.email);
        email.setHint("Email");
        email.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        layout.addView(email);

        password = new EditText(this);
        password.setId(R.id.password);
        password.setHint("Password");
        password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        layout.addView(password);

        Button login = new Button(this);
        login.setId(R.id.login);
        login.setText("Sign in");
        login.setOnClickListener(view -> authenticate());
        layout.addView(login);

        Button clear = new Button(this);
        clear.setId(R.id.clear);
        clear.setText("Clear");
        clear.setOnClickListener(view -> {
            email.setText("");
            password.setText("");
            status.setText("");
        });
        layout.addView(clear);

        status = new TextView(this);
        status.setId(R.id.status);
        status.setTextSize(18);
        layout.addView(status);
        setContentView(layout);
        if (state != null) {
            email.setText(state.getString("email", ""));
            password.setText(state.getString("password", ""));
            status.setText(state.getString("status", ""));
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle state) {
        state.putString("email", email.getText().toString());
        state.putString("password", password.getText().toString());
        state.putString("status", status.getText().toString());
        super.onSaveInstanceState(state);
    }

    private void authenticate() {
        String emailValue = email.getText().toString().trim();
        String passwordValue = password.getText().toString();
        if (emailValue.isEmpty()) {
            status.setText("Email is required");
        } else if (!emailValue.contains("@")) {
            status.setText("Enter a valid email");
        } else if (passwordValue.length() < 8) {
            status.setText("Password must contain at least 8 characters");
        } else if (emailValue.equals("qa@security.test") && passwordValue.equals("Secure123")) {
            status.setText("Dashboard ready");
        } else {
            status.setText("Invalid credentials");
        }
    }
}
